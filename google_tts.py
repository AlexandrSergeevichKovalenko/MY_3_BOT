import os
from livekit.agents import tts
from google.cloud import texttospeech
import io
import wave
from utils import prepare_google_creds_for_tts

class GoogleTTS(tts.TTS):
    def __init__(self, voice_name="de-DE-Wavenet-C"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=16000,
            num_channels=1
        )
        key_path = prepare_google_creds_for_tts()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="de-DE",
            name=voice_name
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000
        )

    async def synthesize(self, text: str) -> tts.SynthesizedAudio:
        input_text = texttospeech.SynthesisInput(text=text)
        response = self.client.synthesize_speech(
            input=input_text,
            voice=self.voice,
            audio_config=self.audio_config
        )
        # Конвертируем аудио в WAV для LiveKit
        audio_buffer = io.BytesIO(response.audio_content)
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(audio_buffer.getvalue())
        wav_buffer.seek(0)
        return tts.SynthesizedAudio(
            text=text,
            data=wav_buffer.read(),
            sample_rate=16000,
            num_channels=1
        )