import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from livekit.api import AccessToken, VideoGrants

# Загружаем переменные окружения (LIVEKIT_API_KEY и LIVEKIT_API_SECRET) из файла .env
load_dotenv()

# --- Настройка Flask-сервера ---
app = Flask(__name__)
# CORS - это механизм безопасности браузера. Эта строка разрешает вашему фронтенду (на localhost:5173)
# делать запросы к этому бэкенду (на localhost:5001).
CORS(app) 

# --- Получение ключей LiveKit из окружения ---
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Проверка, что ключи существуют
if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
    raise RuntimeError("LIVEKIT_API_KEY и LIVEKIT_API_SECRET должны быть установлены в .env файле")

# --- Главная и единственная точка доступа (API Endpoint) ---
@app.route("/token", methods=['GET'])
def get_token():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Имя пользователя обязательно"}), 400

    user_id = username

    # Создаем права доступа
    grant = VideoGrants(
        room_join=True,
        room="sales-assistant-room",
    )

    # Создаем токен с помощью правильной "цепочки" методов
    access_token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
        .with_identity(user_id) \
        .with_name(username) \
        .with_grants(grant) # <--- ИСПРАВЛЕНО ЗДЕСЬ

    # Возвращаем готовый токен
    return jsonify({"token": access_token.to_jwt()})


# --- Запуск сервера ---
if __name__ == '__main__':
    # Запускаем сервер на порту 5001, доступный для всех устройств в вашей сети
    # debug=True автоматически перезагружает сервер при изменениях в коде
    app.run(host="0.0.0.0", port=5001, debug=True)