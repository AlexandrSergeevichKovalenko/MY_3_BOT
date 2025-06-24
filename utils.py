import os
import json
import logging
import tempfile
from pathlib import Path

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
        creds_dict = json.loads(raw_creds)
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as temp_key_file:
            json.dump(creds_dict, temp_key_file)
            temp_key_file.flush()
            temp_path = temp_key_file.name
            logging.info(f"🧪 Сгенерирован временный ключ: {temp_path}")
            return temp_path
    except Exception as e:
        logging.error(f"❌ Ошибка при подготовке Google-кредов: {e}")
        raise