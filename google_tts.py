import os
from livekit.agents import tts
from google.cloud import texttospeech
import io
import wave
from backend.utils import prepare_google_creds_for_tts

class GoogleTTS(tts.TTS):
    def __init__(self, voice_name="en-US-Wavenet-A"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=16000,
            num_channels=1
        )
        key_path = prepare_google_creds_for_tts()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000
        )

    async def synthesize(self, text: str, **kwargs) -> tts.SynthesizedAudio:
        """
        Synthesize text to audio using Google Cloud Text-to-Speech.
        :param text: The text to synthesize.
        :param kwargs: Additional arguments (e.g., conn_options) ignored for non-streaming.
        :return: A context manager yielding a single tts.SynthesizedAudio object.
        """
        class SynthesizeContext:
            def __init__(self, text, client, voice, audio_config):
                self.text = text
                self.client = client
                self.voice = voice
                self.audio_config = audio_config
                self.result = None

            async def __aenter__(self):
                input_text = texttospeech.SynthesisInput(text=self.text)
                response = self.client.synthesize_speech(
                    input=input_text,
                    voice=self.voice,
                    audio_config=self.audio_config
                )
                audio_buffer = io.BytesIO(response.audio_content)
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(16000)
                    wav_file.writeframes(audio_buffer.getvalue())
                wav_buffer.seek(0)
                self.result = tts.SynthesizedAudio(
                    text=self.text,
                    data=wav_buffer.read(),
                    sample_rate=16000,
                    num_channels=1
                )
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.result:
                    result = self.result
                    self.result = None
                    return result
                raise StopAsyncIteration

        return SynthesizeContext(text, self.client, self.voice, self.audio_config)