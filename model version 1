import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Загрузка предобученной модели для получения векторов предложений
model = SentenceTransformer('all-MiniLM-L6-v2')

# Загрузка данных из CSV-файла
def load_knowledge_base(file_path):
    # Загружаем данные в pandas DataFrame
    df = pd.read_csv(file_path)
    # Преобразуем данные в формат списка словарей
    knowledge_base = df.to_dict(orient='records')
    return knowledge_base

# Преобразование вопросов из базы знаний в векторы
def encode_questions(knowledge_base):
    questions = [item['Вопрос'] for item in knowledge_base]
    question_embeddings = model.encode(questions)
    return question_embeddings

# Функция для поиска наиболее схожего вопроса и получения ответа
def get_answer(user_question, knowledge_base):
    # Преобразуем запрос пользователя в вектор
    user_embedding = model.encode([user_question])

    # Преобразуем вопросы из базы знаний в векторы
    question_embeddings = encode_questions(knowledge_base)

    # Вычисляем косинусное сходство между запросом и вопросами в базе знаний
    similarities = cosine_similarity(user_embedding, question_embeddings)

    # Находим индекс самого похожего вопроса
    most_similar_index = np.argmax(similarities)

    # Возвращаем ответ, соответствующий наиболее похожему вопросу
    return knowledge_base[most_similar_index]['Ответ']

# Пример использования
knowledge_base = load_knowledge_base('База данных - Лист1.csv')

user_question = input("Задайте вопрос: ")
answer = get_answer(user_question, knowledge_base)
print(f"Ответ: {answer}")
