import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import joblib
import os

# Загрузка предобученной модели для получения векторов предложений
model = SentenceTransformer('all-MiniLM-L12-v2')

# Загружаем данные из CSV-файла
def load_knowledge_base(file_path):
    # Загружаем данные в pandas DataFrame
    df = pd.read_csv(file_path)
    # Преобразуем данные в формат списка словарей
    knowledge_base = df.to_dict(orient='records')
    return knowledge_base

# Функция для загрузки предвычисленных векторов вопросов
def load_question_embeddings(file_path):
    return joblib.load(file_path)

# Функция для поиска наиболее схожего вопроса и получения ответа
def get_answer(user_question, knowledge_base, question_embeddings):
    # Преобразуем запрос пользователя в вектор
    user_embedding = model.encode([user_question])

    # Вычисляем косинусное сходство между запросом и вопросами в базе знаний
    similarities = cosine_similarity(user_embedding, question_embeddings)

    # Находим индекс самого похожего вопроса
    most_similar_index = np.argmax(similarities)

    # Возвращаем ответ, соответствующий наиболее похожему вопросу
    return knowledge_base[most_similar_index]['Ответ']

# Основная логика для получения ответа
def ask_question():
    # Загрузка базы знаний
    knowledge_base = load_knowledge_base('База данных - Лист1.csv')

    # Файл для сохранения векторов вопросов
    embeddings_file = 'question_embeddings.pkl'

    # Загружаем предвычисленные вектора вопросов
    print("Загружаем предвычисленные вектора вопросов...")
    question_embeddings = load_question_embeddings(embeddings_file)

    # Запрос от пользователя
    user_question = input("Задайте вопрос: ")
    answer = get_answer(user_question, knowledge_base, question_embeddings)
    print(f"Ответ: {answer}")

# Запуск процесса получения ответа на вопрос
ask_question()