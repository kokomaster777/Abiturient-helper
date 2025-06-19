# admin_bot.py

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command
import sqlite3
import csv
import os
from contextlib import closing
from dotenv import load_dotenv
import logging

# Загрузка .env
load_dotenv()
BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

# Список разрешенных ID администраторов
ADMIN_IDS = []  # Замените эти значения на реальные ID администраторов

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Админская клавиатура
admin_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
admin_keyboard.add(
    KeyboardButton("📤 Выгрузить оценки"),
    KeyboardButton("📤 Выгрузить вопросы")
)

# Путь к базам
FEEDBACK_DB = "feedback_log.db"
QUESTIONS_DB = "questions_log.db"

# Проверка прав доступа
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Команда старта
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    await message.answer("Привет, админ!", reply_markup=admin_keyboard)

# Обработка кнопок
@dp.message_handler(lambda message: message.text == "📤 Выгрузить оценки")
async def send_feedback_csv(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    try:
        csv_filename = "feedback_export.csv"
        with closing(sqlite3.connect(FEEDBACK_DB)) as conn:
            cursor = conn.execute("SELECT id, message_id, question_text, bot_answer, feedback, user_id, timestamp FROM feedbacks")
            rows = cursor.fetchall()

        with open(csv_filename, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["id", "message_id", "question_text", "bot_answer", "feedback", "user_id", "timestamp"])
            writer.writerows(rows)

        await message.answer_document(types.InputFile(csv_filename))
        os.remove(csv_filename)
    except Exception as e:
        await message.reply(f"Ошибка при экспорте feedbacks: {e}")

@dp.message_handler(lambda message: message.text == "📤 Выгрузить вопросы")
async def send_questions_csv(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    try:
        csv_filename = "questions_export.csv"
        with closing(sqlite3.connect(QUESTIONS_DB)) as conn:
            cursor = conn.execute("SELECT id, question, timestamp FROM questions_log")
            rows = cursor.fetchall()

        with open(csv_filename, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["id", "question", "timestamp"])
            writer.writerows(rows)

        await message.answer_document(types.InputFile(csv_filename))
        os.remove(csv_filename)
    except Exception as e:
        await message.reply(f"Ошибка при экспорте questions: {e}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
