import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# 1. Загружаем настройки точно так же, как в агенте
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL_RAILWAY")
USER_ID_TO_CHECK = 117649764  # Ваш ID

def check_user_in_db():
    print("--- НАЧАЛО ПРОВЕРКИ ---")
    
    # Проверка URL
    if not DATABASE_URL:
        print("❌ ОШИБКА: DATABASE_URL_RAILWAY пустой!")
        return
    
    # Показываем, куда стучимся (скрывая пароль)
    try:
        host = DATABASE_URL.split("@")[1].split(":")[0]
        print(f"📡 Подключаемся к хосту: {host}")
    except:
        print(f"📡 URL (raw): {DATABASE_URL}")

    try:
        # Подключение
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        print("✅ Подключение к базе успешно!")

        # 1. Проверка таблицы прогресса (Имя)
        print(f"\n🔍 Ищем пользователя {USER_ID_TO_CHECK} в bt_3_user_progress...")
        cursor.execute("SELECT username, user_id FROM bt_3_user_progress WHERE user_id = %s;", (USER_ID_TO_CHECK,))
        user_data = cursor.fetchone()
        
        if user_data:
            print(f"🎉 ПОЛЬЗОВАТЕЛЬ НАЙДЕН! Имя: {user_data[0]}, ID: {user_data[1]}")
        else:
            print("❌ ПОЛЬЗОВАТЕЛЬ НЕ НАЙДЕН в таблице bt_3_user_progress.")
            # Давайте проверим, есть ли вообще кто-то
            cursor.execute("SELECT count(*) FROM bt_3_user_progress;")
            count = cursor.fetchone()[0]
            print(f"ℹ️ Всего записей в таблице: {count}")

        # 2. Проверка таблицы ошибок (Ошибки)
        print(f"\n🔍 Ищем ошибки для {USER_ID_TO_CHECK} в bt_3_detailed_mistakes...")
        cursor.execute("SELECT count(*) FROM bt_3_detailed_mistakes WHERE user_id = %s;", (USER_ID_TO_CHECK,))
        mistakes_count = cursor.fetchone()[0]
        
        if mistakes_count > 0:
            print(f"✅ Найдено ошибок: {mistakes_count}")
        else:
            print("⚠️ Ошибок не найдено (0 rows).")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПОДКЛЮЧЕНИЯ: {e}")

if __name__ == "__main__":
    check_user_in_db()