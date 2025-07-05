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
from datetime import datetime

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

# Путь к базам и CSV-файлам
FEEDBACK_DB = "feedback_log.db"
QUESTIONS_DB = "questions_log.db"
FEEDBACK_CSV = "feedback_history.csv"
QUESTIONS_CSV = "questions_history.csv"

# Проверка прав доступа
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def merge_with_existing_csv(db_path: str, csv_path: str, headers: list, query: str):
    """Объединяет данные из БД с существующим CSV-файлом"""
    try:
        # Читаем существующие данные из CSV
        existing_data = []
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                existing_data = [row for row in reader]

        # Получаем новые данные из БД
        with closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.execute(query)
            new_data = cursor.fetchall()

        # Объединяем данные
        merged_data = existing_data + [
            dict(zip(headers, row)) for row in new_data
        ]

        # Удаляем дубликаты по ID
        seen_ids = set()
        unique_data = []
        for row in merged_data:
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                unique_data.append(row)

        # Сортируем по timestamp (если есть в данных)
        if "timestamp" in headers:
            unique_data.sort(key=lambda x: x["timestamp"], reverse=True)

        # Записываем обратно в CSV
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=";")
            writer.writeheader()
            writer.writerows(unique_data)

        return csv_path
    except Exception as e:
        logging.error(f"Error merging CSV: {e}")
        raise

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
        # Объединяем данные
        csv_path = merge_with_existing_csv(
            db_path=FEEDBACK_DB,
            csv_path=FEEDBACK_CSV,
            headers=["id", "message_id", "question_text", "bot_answer", "feedback", "user_id", "timestamp"],
            query="SELECT id, message_id, question_text, bot_answer, feedback, user_id, timestamp FROM feedbacks"
        )

        # Отправляем файл
        await message.answer_document(types.InputFile(csv_path))
    except Exception as e:
        await message.reply(f"Ошибка при экспорте feedbacks: {e}")

@dp.message_handler(lambda message: message.text == "📤 Выгрузить вопросы")
async def send_questions_csv(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    try:
        # Объединяем данные
        csv_path = merge_with_existing_csv(
            db_path=QUESTIONS_DB,
            csv_path=QUESTIONS_CSV,
            headers=["id", "question", "timestamp"],
            query="SELECT id, question, timestamp FROM questions_log"
        )

        # Отправляем файл
        await message.answer_document(types.InputFile(csv_path))
    except Exception as e:
        await message.reply(f"Ошибка при экспорте questions: {e}")

if __name__ == "__main__":
    # Создаем CSV-файлы при первом запуске, если их нет
    if not os.path.exists(FEEDBACK_CSV):
        with open(FEEDBACK_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["id", "message_id", "question_text", "bot_answer", "feedback", "user_id", "timestamp"])

    if not os.path.exists(QUESTIONS_CSV):
        with open(QUESTIONS_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["id", "question", "timestamp"])

    executor.start_polling(dp, skip_updates=True)
