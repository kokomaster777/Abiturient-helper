import pandas as pd
from sentence_transformers import SentenceTransformer
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

# Функция для сохранения векторов вопросов
def save_question_embeddings(knowledge_base, file_path):
    questions = [item['Вопрос'] for item in knowledge_base]
    question_embeddings = model.encode(questions)
    joblib.dump(question_embeddings, file_path)

# Основная логика для сохранения векторов
def compute_and_save_embeddings():
    # Загрузка базы знаний
    knowledge_base = load_knowledge_base('База данных - Лист1.csv')

    # Файл для сохранения векторов вопросов
    embeddings_file = 'question_embeddings.pkl'

    # Вычисляем и сохраняем вектора вопросов
    print("Вычисляем и сохраняем вектора вопросов...")
    save_question_embeddings(knowledge_base, embeddings_file)
    print(f"Вектора сохранены в файл: {embeddings_file}")

# Запуск процесса сохранения векторов
compute_and_save_embeddings()
