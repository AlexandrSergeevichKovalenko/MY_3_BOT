import os
from livekit.agents import llm
from openai import AsyncOpenAI
import asyncio
from database import get_topic_by_id, get_all_topics

class LanguageMentorTools:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

    @llm.function_tool
    async def check_grammar(self, text: str, language: str = "de") -> tuple[str, str]:
        """Проверяет грамматику текста через Assistant API."""
        thread = await self.client.beta.threads.create()
        await self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"""
            Проверьте текст на грамматические и стилистические ошибки (язык: {language}).
            Текст: "{text}"
            Верните:
            1. Исправленный текст или подтверждение, что ошибок нет.
            2. Список ошибок (если есть).
            """
        )
        run = await self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        )
        while run.status != "completed":
            run = await self.client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            await asyncio.sleep(0.5)
        messages = await self.client.beta.threads.messages.list(thread_id=thread.id)
        result = messages.data[0].content[0].text.value
        corrected_text = result.split("Ошибки:")[0].strip()
        errors = result.split("Ошибки:")[1].strip() if "Ошибки:" in result else ""
        return corrected_text, errors

    @llm.function_tool
    async def choose_topic(self, topic: str) -> dict:
        """Выбирает тему диалога."""
        topics = await get_all_topics()
        for t in topics:
            if topic.lower() in t["name"].lower():
                return {"topic": t["name"], "topic_id": t["id"]}
        return {"topic": topics[0]["name"], "topic_id": topics[0]["id"]}