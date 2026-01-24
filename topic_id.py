import logging
import os
from telegram.ext import Application
from telegram.ext import MessageHandler, filters

logging.basicConfig(level=logging.INFO)


async def debug_update(update, context):
    msg = update.effective_message
    if not msg:
        return
    #print(type(msg))
    logging.info("chat_id: %s", msg.chat_id)
    logging.info("thread_id: %s", msg.message_thread_id)
    logging.info("text: %s", msg.text)

    await context.bot.send_message(
        chat_id=msg.chat_id,
        text=f"chat_id: {msg.chat_id}\nthread_id: {msg.message_thread_id}\ntext: {msg.text}",
        message_thread_id=msg.message_thread_id

    )

def main():
    # # === Настройки бота ===
    TELEGRAM_Deutsch_BOT_TOKEN = os.getenv("TELEGRAM_Deutsch_BOT_TOKEN")

    if TELEGRAM_Deutsch_BOT_TOKEN:
        logging.info("✅ TELEGRAM_Deutsch_BOT_TOKEN успешно загружен!")
    else:
        logging.error("❌ TELEGRAM_Deutsch_BOT_TOKEN не загружен! Проверьте переменные окружения.")

    # ID группы
    BOT_GROUP_CHAT_ID_Deutsch = -1002607222537

    if BOT_GROUP_CHAT_ID_Deutsch:
        logging.info("✅ GROUP_CHAT_ID успешно загружен!")
    else:
        logging.error("❌ GROUP_CHAT_ID не загружен! Проверьте переменные окружения.")

    BOT_GROUP_CHAT_ID_Deutsch = int(BOT_GROUP_CHAT_ID_Deutsch)

    application = Application.builder().token(TELEGRAM_Deutsch_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, debug_update))

    application.run_polling()



if __name__ == "__main__":
    main()
