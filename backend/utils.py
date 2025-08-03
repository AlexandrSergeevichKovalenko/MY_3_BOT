import os
import json
import logging
import tempfile
from pathlib import Path

'''
В контексте ассистента по продажам, эта функция будет вызвана модулем, 
ответственным за преобразование текста в речь (TTS), чтобы обеспечить его доступ к Google Text-to-Speech API.
'''

def prepare_google_creds_for_tts():
    """Подготавливает файл с Google-ключами для google_tts.py."""
    logging.info("🧪 Функция prepare_google_creds_for_tts вызвана")
    
    # Проверяем GOOGLE_APPLICATION_CREDENTIALS
    direct_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if direct_path and Path(direct_path).exists():
        logging.info(f"🌐 Используется GOOGLE_APPLICATION_CREDENTIALS: {direct_path}")
        return direct_path
    
    # Проверяем GOOGLE_CREDS_JSON
    raw_creds = os.getenv("GOOGLE_CREDS_JSON")
    if not raw_creds:
        logging.error("❌ Не найдены GOOGLE_APPLICATION_CREDENTIALS или GOOGLE_CREDS_JSON")
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS или GOOGLE_CREDS_JSON не установлены")
    
    try:
        #Десериализует (преобразует из строки) JSON-строку raw_creds в Python-словарь.
        creds_dict = json.loads(raw_creds)
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as temp_key_file:
            # Сериализует Python-словарь creds_dict в JSON-формат и записывает его в temp_key_file.
            json.dump(creds_dict, temp_key_file)
            # Принудительно записывает все буферизованные данные из памяти на диск.Гарантирует, что содержимое JSON-ключа действительно записано в файл, 
            # прежде чем мы попытаемся использовать этот файл. Без flush() данные могут оставаться в буфере Python и не быть доступны для других процессов.
            temp_key_file.flush()
            #Получает полный путь к созданному временному файлу.
            temp_path = temp_key_file.name
            logging.info(f"🧪 Сгенерирован временный ключ: {temp_path}")
            return temp_path
    except Exception as e:
        logging.error(f"❌ Ошибка при подготовке Google-кредов: {e}")
        raise