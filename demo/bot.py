import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np

# Инициализация бота
API_TOKEN = 'TOKEN'  # Замените на свой API token
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Загрузка предобученной модели для получения векторов предложений
model = SentenceTransformer('all-MiniLM-L6-v2')

# Загрузка данных из CSV-файла
def load_knowledge_base(file_path):
    df = pd.read_csv(file_path)
    knowledge_base = df.to_dict(orient='records')
    return knowledge_base

# Преобразование вопросов из базы знаний в векторы
def encode_questions(knowledge_base):
    questions = [item['Вопрос'] for item in knowledge_base]
    question_embeddings = model.encode(questions)
    return question_embeddings

# Функция для поиска наиболее схожего вопроса и получения ответа
def get_answer(user_question, knowledge_base):
    user_embedding = model.encode([user_question])
    question_embeddings = encode_questions(knowledge_base)
    similarities = cosine_similarity(user_embedding, question_embeddings)
    most_similar_index = np.argmax(similarities)
    return knowledge_base[most_similar_index]['Ответ']

# Загрузка базы знаний
knowledge_base = load_knowledge_base('База данных - Лист1.csv')

# Логирование
logging.basicConfig(level=logging.INFO)

# Хэндлер для команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Задайте ваш вопрос, и я постараюсь ответить.")

# Хэндлер для текста (обрабатывает вопросы пользователя)
@dp.message_handler(lambda message: message.text != "Задать новый вопрос")
async def answer_question(message: types.Message):
    user_question = message.text
    answer = get_answer(user_question, knowledge_base)
    
    # Отправка ответа на вопрос
    await message.reply(f"Ответ: {answer}\n", reply_markup=types.ReplyKeyboardRemove())

    # Кнопка для нового вопроса
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Задать новый вопрос"))
    await message.answer("Нажмите на кнопку для продолжения", reply_markup=markup)

# Хэндлер для кнопки "Задать новый вопрос"
@dp.message_handler(lambda message: message.text == "Задать новый вопрос")
async def new_question(message: types.Message):
    await message.answer("Задайте ваш вопрос", reply_markup=types.ReplyKeyboardRemove())

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
