import os
import json
import logging
from livekit.agents import llm
import asyncio
from typing import Optional, List, Dict
# Импортируем все необходимые функции из нашего обновленного database.py
from database import (
    get_client_by_identifier,
    create_client,
    get_new_products,
    get_product_by_name,
    record_order,
    get_manager_contact_by_location
)

# Файл api.py — это четко определенный интерфейс между возможностями вашего приложения и языковой моделью. 
# Он "обертывает" функции работы с базой данных в "инструменты", которые LLM может понимать и запрашивать для выполнения задач.

# Когда вы помечаете асинхронную функцию @llm.function_tool декоратором, LiveKit Agents автоматически:
# Создает JSON Schema описание этой функции. Это описание включает имя функции, её docstring
# Передает это JSON Schema описание в LLM. Таким образом, LLM "узнаёт", какие функции ей доступны, что они делают и как их вызывать.
# Обрабатывает вызовы LLM. Когда LLM решает вызвать одну из этих функций, 
# LiveKit Agents перехватывает этот вызов и выполняет соответствующий метод in Python-коде.

# пример того как возвращает информацию LLM для вызова функций соответствующей
# {
#   "tool_calls": [
#     {
#       "function": {
#         "name": "get_client_info",
#         "arguments": {
#           "identifier": "0501234567"
#         }
#       }
#     }
#   ]
# }

# риложение (LiveKit Agent) получает этот JSON-объект с вызовом инструмента от LLM.
# Затем фактически вызывает вашу Python-функцию get_client_info (которая находится в классе SalesAssistantTools в api.py) 
# с этими аргументами: await self.tools.get_client_info(identifier="0501234567").
# Результат выполнения Python-функции (например, { "id": 123, "first_name": "Анна", ... }) передается обратно LLM.
# LLM, имея теперь этот результат, формулирует окончательный ответ пользователю на естественном языке, например: "Добрий день, Анно! Радий вас знову чути. Чим можу допомогти?"

# Когда мы просим LLM вызвать функцию, она не "выполняет" 
# код Python напрямую и не "строит" сложные Python-объекты (вроде списка словарей list[dict]) в своей внутренней среде, а затем передает их в нашу функцию.
# LLM генерирует текстовое представление вызова функции. Это текстовое представление должно быть таким, 
# чтобы наша программа на Python могла его легко "прочитать" и "понять", во что это текстовое представление должно быть преобразовано для вызова реальной функции.
# Он делает это в формате JSON, потому что мы ему так сказали в docstring функции, и он знает, что JSON – это универсальный, структурированный текстовый формат.
# LLM не может генерировать list[dict] напрямую!!!
#Потому что LLM – это текстовые модели. Их выход – всегда текст. 
# Когда они генерируют "вызов функции", они фактически генерируют текст, который соответствует заранее определенному JSON-формату вызова. 
# В этом JSON-формате значения аргументов функции также должны быть представлены в виде текста: строки, числа, булевы значения. 
# Для более сложных структур данных, таких как списки словарей, стандартный способ передать их через текстовый интерфейс – это сериализовать их в JSON-строку.

class SalesAssistantTools:
    def __init__(self):
        pass

    @llm.function_tool
    async def get_client_info(self, identifier: str) -> Dict:
        """
        Retrieves client information by system ID or phone number.
        Parameters:
        - identifier: string (required) - The client's system ID or full phone number.
        Returns: A dictionary with client data (id, first_name, last_name, phone_number, email, location, manager_contact, is_existing_client)
                 or an empty dictionary if the client is not found.
        """
        client_data = await get_client_by_identifier(identifier)
        return client_data if client_data else {}

    @llm.function_tool
    async def create_or_update_client(
        self,
        first_name: str,
        phone_number: str,
        last_name: Optional[str] = None,
        system_id: Optional[str] = None,
        email: Optional[str] = None,
        location: Optional[str] = None,
        manager_contact: Optional[str] = None,
        is_existing_client: Optional[bool] = False
    ) -> Dict:
        """
        Creates a new client record or updates an existing one in the database.
        Used when the assistant collects all necessary client information.
        If a client with the given phone number already exists, their data will be updated.
        Parameters:
        - first_name: string (required) - The client's first name.
        - phone_number: string (required) - The client's phone number (must be unique).
        - last_name: string (optional) - The client's surname.
        - system_id: string (optional) - The client's unique system ID.
        - email: string (optional) - The client's email address.
        - location: string (optional) - The client's city or region.
        - manager_contact: string (optional) - Contact details of the responsible manager.
        - is_existing_client: boolean (optional) - True if the client is already working with us, False otherwise.
        Returns: A dictionary with the created/updated client's data.
        """
        if not phone_number:
            raise ValueError("phone_number must not be empty")
        return await create_client(
            first_name, phone_number, last_name, system_id, email, location, manager_contact, is_existing_client
        )

    @llm.function_tool
    async def get_new_products_info(self) -> List[Dict]:
        """
        Retrieves a list of all products marked as new.
        Used when the user asks about new arrivals or company novelties.
        Returns: A list of dictionaries, each containing 'id', 'name', 'description', 'price' of new products.
        """
        return await get_new_products()

    @llm.function_tool
    async def get_product_details(self, product_name: str) -> Dict:
        """
        Retrieves detailed information about a specific product by its name.
        Used when the user is interested in a particular product.
        Parameters:
        - product_name: string (required) - The name of the product.
        Returns: A dictionary with product data (id, name, description, price, available_quantity)
                 or an empty dictionary if the product is not found.
        """
        product_data = await get_product_by_name(product_name)
        return product_data if product_data else {}

    @llm.function_tool
    async def record_customer_order(
        self,
        client_id: int,
        products_info: str, #параметр products_info формируется на основе разговора с клиентом. Конкретно, это делает языковая модель (LLM), которая интегрирована через OpenAI API и используется LiveKit Agents.
        status: str = 'pending'
    ) -> str:
        """
        Records a new order in the database.
        Used when the user is ready to place a purchase.
        Important: The LLM must convert the list of products and their quantities into a JSON string for the 'products_info' parameter.
        Example 'products_info': '[{"product_id": 1, "quantity": 2}, {"product_id": 4, "quantity": 1}]'
        Parameters:
        - client_id: integer (required) - The ID of the client placing the order (obtained from get_client_info or create_or_update_client).
        - products_info: string (required) - A JSON string representing a list of dictionaries, each containing 'product_id' (integer) and 'quantity' (integer).
        - status: string (optional) - The status of the order (e.g., 'pending', 'completed', 'cancelled'). Defaults to 'pending'.
        Returns: A JSON string with the recorded order's data.
        """
        try:
            products_with_quantity = json.loads(products_info)
            if not isinstance(products_with_quantity, list):
                raise ValueError("products_info must be a JSON string representing a list.")
            for item in products_with_quantity:
                if not isinstance(item, dict) or "product_id" not in item or "quantity" not in item:
                    raise ValueError("Each item in products_info must be a dictionary with 'product_id' and 'quantity'.")
        except json.JSONDecodeError as e: 
            #Если строка JSON некорректна (например, содержит синтаксические ошибки), возникает json.JSONDecodeError, который логируется, 
            # и выбрасывается ValueError с описанием проблемы.
            logging.error(f"Invalid JSON in products_info: {products_info}, error: {e}")
            raise ValueError(f"products_info must be a valid JSON string, got: {products_info}")
        order_result = await record_order(client_id, products_with_quantity, status)
        return json.dumps(order_result) # Преобразуем результат в строку JSON

    @llm.function_tool
    async def get_manager_for_location(self, location: str) -> Dict:
        """
        Retrieves the contact details of the manager responsible for the specified location.
        Used when the user asks who their manager is or who is responsible for a specific region.
        Parameters:
        - location: string (required) - The client's city or region.
        Returns: A dictionary with the manager's contact details (e.g., {'contact': 'Name: John Doe, Phone: +123456789'})
                 or an empty dictionary if no manager is found for the location.
        """
        contact = await get_manager_contact_by_location(location)
        return {"contact": contact} if contact else {}