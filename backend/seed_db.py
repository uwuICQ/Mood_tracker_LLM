# seed_db.py

import json
import random
from pathlib import Path
from database import SessionLocal, engine, Base
from database import Message, MoodAnalysis, Session, User


def main():
    # Загружаем словарь эмоций
    Base.metadata.create_all(bind=engine) 
    print("✅ Таблицы созданы или уже существуют.")
    json_path = Path(__file__).parent / "emotion_dict.json"
    with open(json_path, "r", encoding="utf-8") as f:
        emotion_dict = json.load(f)
    
    emotions = list(emotion_dict.keys())
    print(f"Загружено эмоций из JSON: {len(emotions)}")
    
    db = SessionLocal()
    try:
        # 1. СОЗДАЁМ ПОЛЬЗОВАТЕЛЕЙ (ID 1..67)
        print("\nСоздание пользователей...")
        for i in range(1, 68):
            existing = db.query(User).filter(User.id == i).first()
            if not existing:
                user = User(id=i, username=f"user_{i}")
                db.add(user)
        db.commit()
        print(f"Пользователи с ID 1..67 созданы")
        
        # 2. СОЗДАЁМ СЕССИИ (ID 1..30)
        print("\nСоздание сессий")
        for i in range(1, 31):
            existing = db.query(Session).filter(Session.id == i).first()
            if not existing:
                # Привязываем сессию к случайному пользователю
                random_user_id = random.randint(1, 67)
                session = Session(id=i, user_id=random_user_id, device_info="seed_script")
                db.add(session)
        db.commit()
        print(f"Сессии с ID 1..30 созданы")
        
        # 3. УДАЛЯЕМ СТАРЫЕ ТЕСТОВЫЕ СООБЩЕНИЯ
        print("\nОчистка старых тестовых сообщений")
        old_messages = db.query(Message).filter(Message.text == "мимиммамому мимимамому ЛЯЯЯЯЯЯМ 200").all()
        for msg in old_messages:
            db.delete(msg)
        print(f"Удалено старых сообщений: {len(old_messages)}")
        
        # 4. СОЗДАЁМ 100 НОВЫХ ЗАПИСЕЙ
        print("\nГенерация новых записей")
        for i in range(100):
            # Случайные ID из существующих диапазонов
            random_session_id = random.randint(1, 30)
            random_user_id = random.randint(1, 67)
            
            # Создаём сообщение
            fake_message = Message(
                text="Сгенерированный текст",
                session_id=random_session_id,
                user_id=random_user_id
            )
            db.add(fake_message)
            db.flush()  # получаем fake_message.id
            
            # Выбираем случайную эмоцию
            selected_emotion = random.choice(emotions)
            
            # Создаём запись анализа
            analysis = MoodAnalysis(
                message_id=fake_message.id,
                mood_label=selected_emotion,
                mood_score=round(random.uniform(0.5, 1.0), 2),
                valence=round(random.uniform(-1.0, 1.0), 2),
                arousal=round(random.uniform(0.0, 1.0), 2),
                model_version="1.0.0"
            )
            db.add(analysis)
        
        db.commit()
        print(f"Добавлено 100 записей")
        
        
        #ВЫВОД ИТОГОВОЙ СТАТИСТИКИ
        print("ИТОГОВАЯ СТАТИСТИКА")
        
        user_count = db.query(User).count()
        session_count = db.query(Session).count()
        message_count = db.query(Message).count()
        analysis_count = db.query(MoodAnalysis).count()
        
        print(f"Пользователей: {user_count}")
        print(f"Сессий: {session_count}")
        print(f"Сообщений: {message_count}")
        print(f"Анализов: {analysis_count}")
        
    except Exception as e:
        print(f"\nОШИБКА: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()