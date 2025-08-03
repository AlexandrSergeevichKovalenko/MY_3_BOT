import asyncio
import os
import logging
from logging.handlers import RotatingFileHandler
from livekit import rtc
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, llm, RoomInputOptions
from livekit.plugins import openai, silero
from api import SalesAssistantTools

from dotenv import load_dotenv
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler("sales_assistant.log", maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)

class NoBinaryFilter(logging.Filter):
    def filter(self, record):
        return not isinstance(record.msg, bytes)

logging.getLogger().addFilter(NoBinaryFilter())

SALES_ASSISTANT_SYSTEM_INSTRUCTIONS = """
You are a friendly and professional sales assistant representing the company.
Your goal is to communicate effectively with clients, provide product information,
offer new products, understand needs, and assist with order placement.

**Key Actions and Priorities:**
1. **Client Identification**: Always start the conversation with a greeting and attempt to identify the client.
   Ask for their name, surname, and phone number. Use the `get_client_info` tool
   to search by phone number or system ID.
2. **Request Information for Registration/Update**: If the client is new or their data is incomplete,
   politely ask for their first name and phone number before calling `create_or_update_client`.
   **DO NOT call `create_or_update_client` until you have both first_name and phone_number.**
   Optionally, collect last_name, email, city, system_id, and manager_contact if provided.
3. **Discuss New Products**: If the client shows interest in new products or if the
   conversation allows, offer to discuss new products using `get_new_products_info`.
4. **Product Details**: Answer questions about specific products using `get_product_details`.
5. **Order Placement**: If the client expresses a desire to place an order,
   create it using `record_customer_order`. Always clarify product names and quantities.
   Ensure you have a `client_id` (from `get_client_info` or `create_or_update_client`)
   before calling `record_customer_order`.
6. **Manager Contacts**: If the client asks about their manager or who is responsible for their region,
   use `get_manager_for_location` to provide contact information.
7. **Maintain Dialogue**: Always maintain a positive tone, be polite, and clear.
8. **Language**: Communicate exclusively in ENGLISH.
"""

class SalesAssistantAgent(Agent):
    def __init__(self):
        super().__init__(instructions=SALES_ASSISTANT_SYSTEM_INSTRUCTIONS)
        tools_instance = SalesAssistantTools()
        self._tools = [
            tools_instance.get_client_info,
            tools_instance.create_or_update_client,
            tools_instance.get_new_products_info,
            tools_instance.get_product_details,
            tools_instance.record_customer_order,
            tools_instance.get_manager_for_location,
        ]
        self._current_client_id = None
        logging.debug(f"Loaded tools: {[tool.__name__ for tool in self._tools]}")

    async def on_user_joined(self, participant: rtc.RemoteParticipant):
        logging.info(f"🚪 User {participant.identity} joined.")
        self._current_client_id = None
        try:
            # Упрощённое приветственное сообщение для теста
            greeting = "Hello! I'm your sales assistant. Please provide your name and phone number to start."
            logging.debug(f"Publishing greeting: '{greeting}'")
            await self.say(greeting)
        except Exception as e:
            logging.error(f"❌ Error in on_user_joined: {e}", exc_info=True)
            await self.say("Sorry, an error occurred during startup. Please try again.")

    async def on_user_speech_committed(self, text: str, participant: rtc.RemoteParticipant):
        logging.info(f"🗣️ Client {participant.identity} said: '{text}'")
        logging.debug(f"Audio buffer size: {len(participant.audio.get_data())} bytes")
        try:
            response_content = await self.generate_reply(text)
            if response_content:
                logging.debug(f"Publishing response to LiveKit: '{response_content}'")
                await self.say(response_content)
            else:
                logging.info("LLM did not generate a text response, possibly a tool was called.")
        except Exception as e:
            logging.error(f"❌ Error generating LLM response for user speech: {e}", exc_info=True)
            await self.say("Sorry, an error occurred while processing your request. Please try again.")
    
    # этот метод вызывается фреймворком автоматически сразу после того, как generate_reply возвращает None, 
    # it means that LLM вместо текста вернула специальный объект с запросом на вызов функции.
    # модель возвращает строку JSON. Но код получает словарь, потому что фреймворк LIVEKIT выполняет работу по преобразованию строки в словарь за вас. 
    # Это одна из его ключевых задач — избавить вас от рутинной работы по парсингу и предоставить данные в удобном для Python виде.
    # # Псевдокод того, что делает фреймворк "под капотом"
    # json_string_from_llm = '{"identifier": "0501234567"}'
    # arguments_dict = json.loads(json_string_from_llm)
    # arguments_dict теперь является настоящим Python-словарем: {'identifier': '0501234567'}
    async def on_function_call(self, name: str, arguments: dict):
        logging.info(f"🤖 LLM requested function call: {name} with arguments: {arguments}")
        try:
            tool_func = next((tool for tool in self._tools if tool.__name__ == name), None)
            if tool_func:
                if name == "create_or_update_client" and not arguments.get("phone_number"):
                    logging.error("❌ Attempted to call create_or_update_client with empty phone_number")
                    await self.say("Please provide your phone number to proceed with registration.")
                    return
                # **arguments: Это синтаксис распаковки словаря. Он берет словарь arguments (например, {'identifier': '0501234567'}) 
                # и превращает его в именованные аргументы при вызове функции. То есть, строка выше эквивалентна: func_result = await tool_func(identifier='0501234567')
                # в коде on_function_call нет ни одной строки, которая бы явно отправляла func_result в LLM. 
                # И это потому, что эту работу тоже берет на себя главный цикл фреймворка AgentSession.
                func_result = await tool_func(**arguments)
                logging.info(f"✅ Result of function '{name}': {func_result}")
                if (name == "get_client_info" or name == "create_or_update_client") and func_result and "id" in func_result:
                    self._current_client_id = func_result["id"]
                    logging.info(f"🆔 Set current_client_id: {self._current_client_id}")
            else:
                logging.error(f"❌ Tool function '{name}' not found.")
                await self.say(f"Sorry, the function '{name}' was not found.")
        except Exception as e:
            logging.error(f"❌ Error executing function '{name}': {e}", exc_info=True)
            await self.say(f"Sorry, an error occurred while executing '{name}': {e}.")
        # После того как on_function_call успешно завершается, фреймворк делает следующий шаг. 
        # Он берет результат func_result, упаковывает его в специальное сообщение с "ролью" function и снова отправляет всю историю диалога + этот результат в LLM.
        # Теперь у LLM есть вся информация для финального ответа. Например:
        # История: "Привет" -> "Привет! Назовитесь" -> "Я Иван"
        # Результат функции: {'id': 1, 'first_name': 'Иван', 'is_existing_client': True}
        # На основе этого LLM сгенерирует осмысленный ответ: 
        # "Добрый день, Иван! Рад вас снова слышать. Чем могу помочь?". 
        # Этот текст будет получен и озвучен на следующей итерации цикла, через generate_reply и say

    # Это "хук" (hook), который срабатывает после того, как on_function_call завершился. 
    # Он дает вам доступ не только к имени и аргументам, но и к результату (result) или ошибке (error), если она произошла.
    async def on_function_call_ended(self, name: str, success: bool, result: dict | str | None):
        logging.info(f"🏁 Function call '{name}' completed. Success: {success}. Result: {result}")

    async def say(self, text: str):
        logging.debug(f"Attempting to publish audio for text: '{text}'")
        try:
            await super().say(text)
            logging.debug("Audio published successfully")
        except Exception as e:
            logging.error(f"❌ Failed to publish audio: {e}", exc_info=True)

async def entrypoint(ctx: JobContext):
    logging.info("✨ Starting entrypoint for Sales Assistant Agent...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logging.error("❌ OPENAI_API_KEY is not set")
        raise ValueError("OPENAI_API_KEY environment variable is required")
    session = AgentSession(
        stt=openai.STT(
            model="whisper-1",
            language="en",
            api_key=api_key
        ),
        llm=openai.LLM(
            model="gpt-4o-mini",
            api_key=api_key
        ),
        tts=openai.TTS(
            model="tts-1",
            voice="alloy",
            api_key=api_key
        ),
        vad=silero.VAD.load(),
    )
    await session.start(
        room=ctx.room,
        agent=SalesAssistantAgent(),
        room_input_options=RoomInputOptions(noise_cancellation=None)
    )
    await ctx.connect()
    logging.info("✅ AgentSession started. Waiting for the first user message.")

# Про ключи (LIVEKIT_API_KEY и SECRET):
# Вы правы, мы не передаем их в entrypoint явно. И не нужно. Библиотека livekit-agents (и многие другие серверные программы) по умолчанию спроектирована так, 
# что она автоматически ищет эти данные в переменных окружения. Когда вы запускаете python agent.py, 
# библиотека сама выполняет невидимый для вас os.getenv("LIVEKIT_API_KEY") и os.getenv("LIVEKIT_API_SECRET") для аутентификации на сервере LiveKit. 
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))



# Вот полная последовательность событий, начиная с конца on_user_speech_committed:
# on_user_speech_committed завершается. generate_reply вернул None, сигнализируя о вызове функции.
# Дирижер (фреймворк) видит этот сигнал и вызывает вашего первого музыканта: await on_function_call(...).
# Ваш код в on_function_call выполняется. Он находит функцию, вызывает ее и получает func_result (например, словарь с данными Ивана). 
# Метод on_function_call завершает свою работу.Дирижер (фреймворк) перехватывает управление. Он видит, что on_function_call успешно завершился, и у него на руках есть func_result.
# Вот он, скрытый шаг! Дирижер берет func_result, преобразует его в JSON-строку (если это словарь) и добавляет в историю диалога как новое сообщение со специальной ролью function.
# История диалога теперь выглядит так:
# [
#  {'role': 'user', 'content': 'Здравствуйте, это Иван'},
#  {'role': 'assistant', 'tool_calls': [...]}, // Запрос на вызов get_client_info
#  {'role': 'function', 'name': 'get_client_info', 'content': '{"id": 1, "first_name": "Иван", ...}'} // <-- РЕЗУЛЬТАТ
# ]
# Дирижер (фреймворк) немедленно делает новый автоматический вызов LLM, отправляя ей всю эту обновленную историю.
# LLM получает всю картину: что спросил пользователь, какой инструмент она решила вызвать, и какой результат этот инструмент вернул.
# Теперь у LLM есть все данные, и на этот раз она генерирует текстовый ответ: "Добрый день, Иван! Рад вас снова слышать. Чем могу помочь?".
# Дирижер (фреймворк) получает этот текстовый ответ и понимает, что теперь нужно просто его озвучить. Он вызывает вашего второго музыканта: await self.say(...).