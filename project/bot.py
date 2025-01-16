from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import asyncio
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import joblib

# Создаем экземпляры бота и диспетчера
API_TOKEN = "7654821181:AAG0mL--V7K_8zKXQOWXPWb-yd2EQlJCCKU"
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Глобальные переменные для базы знаний и векторов
knowledge_base = None
question_embeddings = None
model = None

# Кнопки
button_ask_question = KeyboardButton("Задать вопрос")
keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(button_ask_question)

# Функции для работы с базой знаний

def load_knowledge_base(file_path):
    df = pd.read_csv(file_path)
    return df.to_dict(orient='records')

def load_question_embeddings(file_path):
    return joblib.load(file_path)

def get_answer(user_question, knowledge_base, question_embeddings):
    user_embedding = model.encode([user_question])
    similarities = cosine_similarity(user_embedding, question_embeddings)
    most_similar_index = np.argmax(similarities)
    return knowledge_base[most_similar_index]['Ответ']

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Добрый день, это цифровой помощник", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "Задать вопрос")
async def ask_question(message: types.Message):
    await message.reply("Пожалуйста, задайте чётко сформулированный вопрос.")

@dp.message_handler()
async def handle_question(message: types.Message):
    user_question = message.text
    try:
        answer = get_answer(user_question, knowledge_base, question_embeddings) + '\n\nЕсли вас не устроил ответ, сформулируйте ваш вопрос более чётко'
        await message.reply(answer)
    except Exception as e:
        await message.reply(f"Произошла ошибка при обработке вопроса: {e}")

if __name__ == "__main__":
    # Загружаем базу знаний и векторы один раз при запуске
    print("Загружаем базу знаний и предвычисленные вектора...")
    knowledge_base = load_knowledge_base('База данных - Лист1.csv')
    question_embeddings = load_question_embeddings('question_embeddings.pkl')
    model = SentenceTransformer('all-MiniLM-L12-v2')

    executor.start_polling(dp, skip_updates=True)
