from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import random

# Прямые импорты из текущей папки
from database import SessionLocal, User, Session as DBSession, Message, MoodAnalysis, engine, Base
from emotion_analyzer import analyze_text, mix_colors, emotion_to_rgb, get_supportive_message

from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy import func

app = FastAPI(title="Mood Tracker API", version="1.0.0")

# Авто-создание таблиц при запуске
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],


)

# ============================================
# 2. БАЗА РУССКИХ ФАКТОВ ОБ ЭМОЦИЯХ
# ============================================
RUSSIAN_FUN_FACTS = [
    "Радость заставляет мозг вырабатывать дофамин, который работает как природное обезболивающее.",
    "Гнев повышает температуру тела и учащает пульс — вы буквально 'закипаете'.",
    "Слезы грусти содержат гормоны стресса, поэтому плач буквально выводит стресс из организма.",
    "Чувство удивления длится всего долю секунды, прежде чем сменится другой эмоцией.",
    "Улыбка, даже искусственная, отправляет в мозг сигнал о безопасности и снижает тревогу.",
    "Спокойствие физически увеличивает плотность серого вещества в областях мозга, отвечающих за память."
]

# ============================================
# 3. ПОДРОБНЫЕ МОДЕЛИ ОТВЕТОВ ФРОНТЕНДУ
# ============================================
class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)

class EmotionDetail(BaseModel):
    emotion: str
    intensity: float
    color: str

class AnalyzeResponse(BaseModel):
    emotion: str
    intensity: float
    color: str
    message: str  # <--- Вот та самая мотивирующая фраза!
    all_emotions: List[EmotionDetail]

# ============================================
# 4. ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
# ============================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================
# 5. ЭНДПОИНТЫ
# ============================================

@app.get("/")
def root():
    return {"message": "Mood Tracker API работает на 100%!"}

@app.get("/random-fact")
def get_random_fact():
    """Случайный факт для окна ожидания"""
    return {"fact": random.choice(RUSSIAN_FUN_FACTS)}

@app.get("/stats")
def get_stats(db: SQLAlchemySession = Depends(get_db)):
    """Статистика для Архива (считает прямо из БД)"""
    try:
        results = db.query(
            MoodAnalysis.mood_label, 
            func.count(MoodAnalysis.id)
        ).group_by(MoodAnalysis.mood_label).all()
        return {emotion: count for emotion, count in results}
    except Exception as e:
        print(f"Ошибка БД: {e}")
        return {}

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: TextRequest, db: SQLAlchemySession = Depends(get_db)):
    """Главный эндпоинт: анализ, сохранение в БД и генерация фразы"""
    
    # 1. Анализируем текст
    result = analyze_text(request.text)
    dominant_emotion = result["dominant_emotion"]
    intensity = result["intensity"]
    
    # 2. Вычисляем цвета и достаем мотивирующую фразу
    mixed_rgb = mix_colors(result["emotions"])
    color_hex = f"#{mixed_rgb[0]:02x}{mixed_rgb[1]:02x}{mixed_rgb[2]:02x}"
    support_msg = get_supportive_message(dominant_emotion)
    
    all_emotions = []
    for emotion, em_intensity in result["emotions"].items():
        rgb = emotion_to_rgb(emotion, em_intensity)
        all_emotions.append(EmotionDetail(
            emotion=emotion, intensity=em_intensity, color=f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        ))

    # 3. Сохраняем в твою реляционную Базу Данных
    try:
        # Безопасное создание дефолтного юзера и сессии (чтобы не было ошибок ключей)
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(id=1, username="test_user")
            db.add(user)
            db.commit()
            
        session_db = db.query(DBSession).filter(DBSession.id == 1).first()
        if not session_db:
            session_db = DBSession(id=1, user_id=1)
            db.add(session_db)
            db.commit()

        # Запись самого сообщения
        new_message = Message(text=request.text, user_id=1, session_id=1)
        db.add(new_message)
        db.flush() 
        
        # Запись анализа
        new_analysis = MoodAnalysis(
            message_id=new_message.id,
            mood_label=dominant_emotion,
            mood_score=round(intensity, 2),
            valence=0.0,
            arousal=0.0,
            model_version="1.0.0"
        )
        db.add(new_analysis)
        db.commit() 
    except Exception as e:
        print(f"Ошибка БД: {e}")
        db.rollback() 
    
    # 4. Отдаем результат фронтенду!
    return AnalyzeResponse(
        emotion=dominant_emotion,
        intensity=intensity,
        color=color_hex,
        message=support_msg,  # Отправляем фразу
        all_emotions=all_emotions
    )