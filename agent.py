import asyncio
import os
from livekit import rtc
from livekit.agents import Agent, JobContext, WorkerOptions, cli, stt, llm
from livekit.plugins import openai
from google_tts import GoogleTTS
from api import LanguageMentorTools
from database import save_error, suggest_topic
from bot_3 import get_assistant_id_from_db

class Assistant:
    def __init__(self, model: llm.LLM):
        self._model = model
        self._tools = LanguageMentorTools()

    async def start(self, ctx: JobContext):
        agent = Agent(
            stt=stt.OpenAI(model="whisper-1", language="de"),
            tts=GoogleTTS(voice_name="de-DE-Wavenet-C"),
            llm=self._model,
            fnc_ctx=self._tools,
            chat_ctx=llm.ChatContext(messages=[
                llm.ChatMessage(
                    role="system",
                    content="Du bist ein Deutschlehrer-Mentor. Sprich auf Deutsch, initiiere Gespräche, überprüfe Grammatik, und speichere Fehler в der Datenbank. Begrüße den Benutzer и schlage ein Thema vor."
                )
            ])
        )

        @agent.on("user_joined")
        async def on_user_joined(participant: rtc.RemoteParticipant):
            user_id = participant.identity
            topic = await suggest_topic(user_id)
            greeting = f"Hallo! Ich bin dein Mentor für Deutsch. Lass uns über '{topic}' sprechen. Sage 'Thema wählen', um ein anderes Thema auszuwählen, oder sprich просто, um zu üben!"
            await agent.say(greeting)

        @agent.on("user_speech_committed")
        async def on_user_speech_committed(text: str, participant: rtc.RemoteParticipant):
            user_id = participant.identity
            response, errors = await self._tools.check_grammar(text)
            await save_error(user_id, text, errors, ctx.room.metadata.get("topic_id"))
            await agent.say(response)

            # Инициация диалога
            question = await self._model.generate(
                prompt=f"Stelle eine Frage zum Thema '{ctx.room.metadata.get('topic')}' на Deutsch.",
                tools=[self._tools.choose_topic]
            )
            await agent.say(question)

        @agent.on("function_call")
        async def on_function_call(name: str, arguments: dict):
            if name == "choose_topic":
                topic = arguments.get("topic")
                ctx.room.metadata["topic"] = topic
                ctx.room.metadata["topic_id"] = arguments.get("topic_id")
                await agent.say(f"Thema '{topic}' gewählt. Lass uns sprechen!")

        await agent.start(ctx.room)

async def entrypoint(ctx: JobContext):
    task_name = "mentor_deutsch"  # Укажите task_name, используемый в bot_3.py
    assistant_id = get_assistant_id_from_db(task_name)
    if not assistant_id:
        raise RuntimeError(f"Assistant ID для '{task_name}' не найден в базе")
    
    model = openai.LLM(
        model="gpt-4.1-2025-04-14",
        api_key=os.getenv("OPENAI_API_KEY"),
        assistant_id=assistant_id
    )
    assistant = Assistant(model)
    await assistant.start(ctx)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint))

# WORKING CODE 
# from __future__ import annotations
# from livekit.agents import (
#     AutoSubscribe,
#     JobContext,
#     WorkerOptions,
#     cli,
#     llm,
#     Agent,
#     AgentSession,
# )
# from livekit.plugins import openai
# from dotenv import load_dotenv
# from api import AssistantFnc
# from prompts import WELCOME_MESSAGE, INSTRUCTIONS
# import os
# import json

# load_dotenv()

# async def entrypoint(ctx: JobContext):
#     await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
#     await ctx.wait_for_participant()

#     assistant_fnc = AssistantFnc()
#     agent = Agent(instructions=INSTRUCTIONS, tools=assistant_fnc.get_tools())
#     session = AgentSession(
#         llm=openai.realtime.RealtimeModel(
#             voice="shimmer",
#             temperature=0.8
#         )
#     )
#     await session.start(room=ctx.room, agent=agent)
#     # Отправка приветственного сообщения через publish_data
#     await ctx.room.local_participant.publish_data(
#         json.dumps({"message": WELCOME_MESSAGE, "role": "assistant"}),
#         topic="chat"
#     )
#     print("Published welcome message:", WELCOME_MESSAGE)

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))