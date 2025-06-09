# -*- coding: utf-8 -*-
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from contextlib import closing
import requests
import asyncio
import os
import re

from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

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

# Конфигурация из переменных окружения
CONFIG = {
    "response_delay": float(os.getenv('RESPONSE_DELAY', 0.3)),  # минуты
    "cleanup_interval": int(os.getenv('CLEANUP_INTERVAL', 24)),  # часы
    "max_questions_per_user": int(os.getenv('MAX_QUESTIONS_PER_USER', 50)),  # вопросов в час
    "allowed_chat_id": int(os.getenv('ALLOWED_CHAT_ID')),  # ID вашего чата
    "allowed_topic_id": int(os.getenv('ALLOWED_TOPIC_ID', 2))  # ID темы, где работает бот
}

# API ключи из переменных окружения
IAM_TOKEN = os.getenv('IAM_TOKEN')
FOLDER_ID = os.getenv('FOLDER_ID')
BOT_TOKEN = os.getenv('BOT_TOKEN')

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


def load_system_prompt() -> str:
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Ошибка чтения system_prompt.txt: {e}")
        return "Ты — представитель приёмной комиссии УрФУ."
    
def get_answer(question: str) -> str:
    try:
        system_prompt = load_system_prompt()

        prompt = {
            "modelUri": f"gpt://{FOLDER_ID}/yandexgpt",
            "completionOptions": {
                "temperature": 0.3,
                "maxTokens": 1000
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt
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
        logger.error(f"Yandex API error: {str(e)}")
        return "Не удалось обработать запрос. Попробуйте позже."


def get_feedback_keyboard(message_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👍", callback_data=f"like:{message_id}"),
        InlineKeyboardButton("👎", callback_data=f"dislike:{message_id}")
    )
    return keyboard


def save_feedback_to_file(message_id: int, feedback: str, user_id: int):
    try:
        # Получаем вопрос по message_id
        result = db_execute("SELECT question FROM questions WHERE msg_id=?", (message_id,))
        question_text = result[0][0] if result else "[вопрос не найден]"

        with open("feedback_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Вопрос: \"{question_text}\" | Оценка: {feedback} | От пользователя: {user_id}\n")

        logger.info(f"Оценка сохранена: {'лайк' if feedback == '👍' else 'дизлайк'} на вопрос {message_id}")
    except Exception as e:
        logger.error(f"Ошибка записи оценки в файл: {e}")

#Сохраняет вопрос в файл questions_log.txt
def save_question_to_file(question: str):
    """Сохраняет вопрос в отдельный файл"""
    try:
        with open('questions_log.txt', 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {question}\n")
    except Exception as e:
        logger.error(f"Failed to save question to file: {e}")


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
        
        answer = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', answer)
        
        await bot.send_message(
            chat_id=chat_id,
            message_thread_id=topic_id,
            text=answer,
            reply_to_message_id=message_id,
            parse_mode="HTML",
            reply_markup=get_feedback_keyboard(message_id)

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

        # Проверяем, содержит ли сообщение вопрос (знак "?")
        if '?' not in message.text:
            logger.info(f"Ignoring message without question mark: {message.text}")
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
        
        save_question_to_file(message.text) #сохраняем вопрос в файл

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


#Кнопка для обратной связи на ответ
@dp.callback_query_handler(lambda c: c.data.startswith(('like:', 'dislike:')))
async def handle_feedback(callback_query: types.CallbackQuery):
    try:
        feedback_type, msg_id = callback_query.data.split(':')
        user_id = callback_query.from_user.id
        feedback_text = '👍' if feedback_type == 'like' else '👎'

        save_feedback_to_file(int(msg_id), feedback_text, user_id)

        await callback_query.answer("Спасибо за вашу оценку!", show_alert=False)
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.error(f"Ошибка обработки оценки: {e}")
        await callback_query.answer("Ошибка при попытке сохранить оценку.")



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
