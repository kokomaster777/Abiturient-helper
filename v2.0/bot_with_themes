# -*- coding: utf-8 -*-
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from contextlib import closing
import requests
import asyncio
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
CONFIG = {
    "response_delay": 0.3,  # минуты
    "cleanup_interval": 24,  # часы
    "max_questions_per_user": 50,  # вопросов в час
    "allowed_chat_id": -1002660822294,  # ID вашего чата
    "allowed_topic_id": 2  # ID темы, где работает бот
}

# API ключи (замените на свои)
IAM_TOKEN = ""  # Замените на ваш токен
FOLDER_ID = ""  # Замените на ваш folder_id
BOT_TOKEN = ""

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

# Инициализация базы данных
def init_db():
    if os.path.exists('questions.db'):
        os.remove('questions.db')
    
    with closing(sqlite3.connect('questions.db')) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE questions
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     msg_id INTEGER,
                     chat_id INTEGER,
                     user_id INTEGER,
                     question TEXT,
                     timestamp DATETIME,
                     answered BOOLEAN DEFAULT FALSE,
                     topic_id INTEGER,
                     admin_replied BOOLEAN DEFAULT FALSE)''')  # Добавлено поле для отметки ответа админа
        c.execute('''CREATE TABLE users
                    (user_id INTEGER PRIMARY KEY,
                     last_question_time DATETIME,
                     question_count INTEGER DEFAULT 0)''')
        conn.commit()
        logger.info("Database initialized")

init_db()

def get_answer(question: str) -> str:
    try:
        prompt = {
            "modelUri": f"gpt://{FOLDER_ID}/yandexgpt",
            "completionOptions": {
                "temperature": 0.3,
                "maxTokens": 1000
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Ты помощник приёмной комиссии. Отвечай только на вопросы о поступлении."
                },
                {
                    "role": "user",
                    "text": question
                }
            ]
        }

        response = requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers={
                "Authorization": f"Bearer {IAM_TOKEN}",
                "Content-Type": "application/json"
            },
            json=prompt
        ).json()

        return response['result']['alternatives'][0]['message']['text']
    except Exception as e:
        logger.error(f"Yandex API error: {e}")
        return "Не удалось обработать запрос. Попробуйте позже."

async def send_delayed_response(chat_id: int, message_id: int, topic_id: int):
    """Отправка ответа с задержкой"""
    try:
        # Проверяем, не ответил ли уже админ
        result = db_execute(
            "SELECT admin_replied FROM questions WHERE msg_id=?",
            (message_id,)
        )
        
        if result and result[0][0]:  # Если админ уже ответил
            logger.info(f"Admin already replied to message {message_id}")
            return

        # Получаем вопрос из базы
        question = db_execute(
            "SELECT question FROM questions WHERE msg_id=? AND answered=0",
            (message_id,)
        )
        
        if not question:
            return

        # Ждем указанное время
        await asyncio.sleep(CONFIG['response_delay'] * 60)

        # Проверяем еще раз перед отправкой
        result = db_execute(
            "SELECT admin_replied FROM questions WHERE msg_id=?",
            (message_id,)
        )
        if result and result[0][0]:
            return

        # Получаем и отправляем ответ
        answer = get_answer(question[0][0])
        await bot.send_message(
            chat_id=chat_id,
            message_thread_id=topic_id,
            text=answer,
            reply_to_message_id=message_id
        )

        # Помечаем как отвеченный
        db_execute(
            "UPDATE questions SET answered=1 WHERE msg_id=?",
            (message_id,),
            commit=True
        )
    except Exception as e:
        logger.error(f"Response error: {e}")

def db_execute(query: str, params=(), commit: bool = False):
    """Выполнение SQL запроса"""
    try:
        with closing(sqlite3.connect('questions.db')) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            c = conn.cursor()
            c.execute(query, params)
            if commit:
                conn.commit()
            return c.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return None

async def check_user_limit(user_id: int) -> bool:
    """Проверка лимита вопросов"""
    try:
        result = db_execute(
            "SELECT question_count FROM users WHERE user_id=?",
            (user_id,)
        )
        return not (result and result[0][0] >= CONFIG['max_questions_per_user'])
    except Exception as e:
        logger.error(f"Limit check error: {e}")
        return True

def update_user_limit(user_id: int):
    """Обновление счетчика вопросов"""
    try:
        db_execute(
            '''INSERT OR REPLACE INTO users 
            (user_id, last_question_time, question_count)
            VALUES (?, ?, COALESCE(
                (SELECT question_count FROM users WHERE user_id=?) + 1, 1))''',
            (user_id, datetime.now(), user_id),
            commit=True
        )
    except Exception as e:
        logger.error(f"Limit update error: {e}")

def cleanup_database():
    """Очистка старых записей"""
    try:
        db_execute(
            "DELETE FROM questions WHERE timestamp < ?",
            (datetime.now() - timedelta(days=7),),
            commit=True
        )
        logger.info("Database cleanup completed")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handle_message(message: types.Message):
    """Обработка входящих сообщений"""
    try:
        # Проверяем чат и тему
        if message.chat.id != CONFIG['allowed_chat_id']:
            return
            
        topic_id = getattr(message, 'message_thread_id', 1)
        if topic_id != CONFIG['allowed_topic_id']:
            return

        # Если это ответ админа на сообщение
        if message.reply_to_message:
            if await is_admin(message.chat.id, message.from_user.id):
                # Помечаем, что админ ответил
                db_execute(
                    "UPDATE questions SET admin_replied=1 WHERE msg_id=?",
                    (message.reply_to_message.message_id,),
                    commit=True
                )
                logger.info(f"Admin replied to message {message.reply_to_message.message_id}")
                return

        # Игнорируем сообщения от ботов
        if message.from_user.is_bot:
            return

        # Проверяем лимит
        if not await check_user_limit(message.from_user.id):
            await message.reply(
                f"🚫 Лимит ({CONFIG['max_questions_per_user']} вопросов/час) исчерпан!"
            )
            return

        # Сохраняем вопрос
        db_execute(
            '''INSERT INTO questions 
            (msg_id, chat_id, user_id, question, timestamp, topic_id)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (
                message.message_id,
                message.chat.id,
                message.from_user.id,
                message.text,
                datetime.now(),
                topic_id
            ),
            commit=True
        )
        
        update_user_limit(message.from_user.id)

        # Запускаем отложенный ответ
        asyncio.create_task(
            send_delayed_response(
                chat_id=message.chat.id,
                message_id=message.message_id,
                topic_id=topic_id
            )
        )

    except Exception as e:
        logger.error(f"Message handling error: {e}")

async def is_admin(chat_id: int, user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        return False

async def on_startup(dp):
    """Действия при запуске бота"""
    scheduler.start()
    scheduler.add_job(
        cleanup_database,
        'interval',
        hours=CONFIG['cleanup_interval']
    )
    
    try:
        chat = await bot.get_chat(CONFIG['allowed_chat_id'])
        logger.info(f"Бот запущен в чате: {chat.title} (ID: {chat.id})")
        logger.info(f"Работает в теме с ID: {CONFIG['allowed_topic_id']}")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

if __name__ == "__main__":
    try:
        executor.start_polling(
            dp,
            skip_updates=True,
            on_startup=on_startup
        )
    except Exception as e:
        logger.error(f"Critical error: {e}")
    finally:
        scheduler.shutdown()
        logger.info("Бот остановлен")
