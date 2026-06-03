# database.py
# Подключение к БД и все модели (таблицы)

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    Text, TIMESTAMP, Boolean, ForeignKey, BigInteger, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime

# ============================================
# НАСТРОЙКА ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ
# ============================================
DATABASE_URL = "sqlite:///mood_tracker.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================
# МОДЕЛИ (ТАБЛИЦЫ)
# ============================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, onupdate=datetime.utcnow, nullable=True)
    preferred_theme = Column(String(50), nullable=True, default="auto")

    # Связи
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user")
    ui_feedbacks = relationship("UIFeedback", back_populates="user", cascade="all, delete-orphan")
    experiment_assignments = relationship("ExperimentAssignment", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    ended_at = Column(TIMESTAMP, nullable=True)
    device_info = Column(Text, nullable=True)

    # Связи
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    ui_feedbacks = relationship("UIFeedback", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        end_time = self.ended_at.strftime("%Y-%m-%d %H:%M") if self.ended_at else "активна"
        return f"<Session(id={self.id}, user_id={self.user_id}, ended={end_time})>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Связи
    session = relationship("Session", back_populates="messages")
    user = relationship("User", back_populates="messages")
    mood_analysis = relationship("MoodAnalysis", back_populates="message", uselist=False, cascade="all, delete-orphan")
    ui_feedbacks = relationship("UIFeedback", back_populates="message", cascade="all, delete-orphan")

    def __repr__(self):
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"<Message(id={self.id}, user_id={self.user_id}, text='{preview}')>"


class MoodAnalysis(Base):
    __tablename__ = "mood_analysis"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, unique=True, index=True)
    mood_label = Column(String(50), nullable=False, index=True)
    mood_score = Column(Float, nullable=False)
    valence = Column(Float, nullable=True)
    arousal = Column(Float, nullable=True)
    analysis_timestamp = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    model_version = Column(String(20), nullable=True, default="1.0.0")

    # Связь с сообщением (1:1)
    message = relationship("Message", back_populates="mood_analysis")

    # Гарантируем, что к одному сообщению не привязано два анализа
    __table_args__ = (
        UniqueConstraint("message_id", name="uq_message_mood"),
    )

    def __repr__(self):
        return f"<MoodAnalysis(id={self.id}, message_id={self.message_id}, mood={self.mood_label}, score={self.mood_score})>"


class ColorScheme(Base):
    __tablename__ = "color_schemes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mood_label = Column(String(50), nullable=False, unique=True, index=True)
    primary_color = Column(String(7), nullable=False)
    secondary_color = Column(String(7), nullable=True)
    bg_color = Column(String(7), nullable=True, default="#FFFFFF")

    # Гарантируем, что каждая эмоция имеет только одну цветовую схему
    __table_args__ = (
        UniqueConstraint("mood_label", name="uq_mood_color"),
    )

    def __repr__(self):
        return f"<ColorScheme(id={self.id}, mood='{self.mood_label}', primary={self.primary_color})>"


class UIFeedback(Base):
    __tablename__ = "ui_feedback"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    applied_color = Column(String(7), nullable=False)
    user_reaction = Column(String(20), nullable=False, index=True)
    reaction_timestamp = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    time_spent_on_page = Column(BigInteger, nullable=True)

    # Связи
    user = relationship("User", back_populates="ui_feedbacks")
    message = relationship("Message", back_populates="ui_feedbacks")
    session = relationship("Session", back_populates="ui_feedbacks")

    def __repr__(self):
        return f"<UIFeedback(id={self.id}, user_id={self.user_id}, reaction='{self.user_reaction}')>"


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    start_date = Column(TIMESTAMP, nullable=False)
    end_date = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    target_metric = Column(String(50), nullable=False)
    min_messages_per_user = Column(Integer, nullable=False, default=5)
    traffic_percent = Column(Integer, nullable=False, default=100)

    # Связи
    assignments = relationship("ExperimentAssignment", back_populates="experiment", cascade="all, delete-orphan")

    def __repr__(self):
        status = "активен" if self.is_active else "завершён"
        return f"<Experiment(id={self.id}, name='{self.name}', status={status}, traffic={self.traffic_percent}%)>"


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    group_name = Column(String(50), nullable=False, default="control", index=True)
    assigned_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    color_scheme_override = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Связи
    experiment = relationship("Experiment", back_populates="assignments")
    user = relationship("User", back_populates="experiment_assignments")

    def __repr__(self):
        return f"<ExperimentAssignment(id={self.id}, experiment_id={self.experiment_id}, user_id={self.user_id}, group='{self.group_name}')>"
    

# ============================================
# СОХРАНЕНИЕ ЗАПИСЕЙ В БД
# ============================================
def save_analysis_to_db(text: str, mood_label: str, mood_score: float, 
                         valence: float = None, arousal: float = None,
                         color_hex: str = None, user_id: int = None,
                         session_id: int = None) -> dict:
    
    # Создаём сессию БД
    db = SessionLocal()
    
    try:
        # 1. Создаём запись в таблице messages
        new_message = Message(
            text=text,
            user_id=user_id,
            session_id=session_id,
        )
        db.add(new_message)
        db.flush()  # чтобы получить id нового сообщения (без коммита)
        
        # 2. Создаём запись в таблице mood_analysis
        new_analysis = MoodAnalysis(
            message_id=new_message.id,
            mood_label=mood_label,
            mood_score=mood_score,
            valence=valence,
            arousal=arousal,
        )
        db.add(new_analysis)
        
        # 3. Сохраняем всё в БД
        db.commit()
        
        # 4. Возвращаем результат
        return {
            "success": True,
            "message_id": new_message.id,
            "analysis_id": new_analysis.id,
            "mood_label": mood_label,
            "mood_score": mood_score
        }
        
    except Exception as e:
        # Если ошибка — откатываем изменения
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
        
    finally:
        # Закрываем сессию
        db.close()


# ============================================
# ПОЛУЧЕНИЕ ЗАПИСЕЙ ИЗ БД
# ============================================
def get_all_entries(db: SessionLocal = None) -> list:

    # Если сессия не передана, создаём свою
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    
    try:
        # JOIN messages и mood_analysis
        results = db.query(Message, MoodAnalysis).join(
            MoodAnalysis, Message.id == MoodAnalysis.message_id
        ).order_by(Message.timestamp.desc()).all()  # сортировка: новые сверху
        
        # Преобразуем результат в список словарей
        entries = []
        for message, analysis in results:
            # Получаем цвет для эмоции (из color_schemes, если есть)
            color = db.query(ColorScheme).filter(
                ColorScheme.mood_label == analysis.mood_label
            ).first()
            
            entry = {
                "id": message.id,
                "text": message.text,
                "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                "mood_label": analysis.mood_label,
                "mood_score": analysis.mood_score,
                "valence": analysis.valence,
                "arousal": analysis.arousal,
                "color": {
                    "primary": color.primary_color if color else "#A9A9A9",
                    "secondary": color.secondary_color if color else "#D3D3D3",
                    "bg": color.bg_color if color else "#F5F5F5"
                } if color else None
            }
            entries.append(entry)
        
        return entries
        
    except Exception as e:
        print(f"Ошибка при получении записей: {e}")
        return []
        
    finally:
        if own_session:
            db.close()


def get_entry_by_id(entry_id: int, db: SessionLocal = None):
    
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    
    try:
        # Ищем сообщение с указанным ID
        message = db.query(Message).filter(Message.id == entry_id).first()
        if not message:
            return None
        
        # Ищем связанный анализ
        analysis = db.query(MoodAnalysis).filter(
            MoodAnalysis.message_id == entry_id
        ).first()
        
        if not analysis:
            return None
        
        # Получаем цвет
        color = db.query(ColorScheme).filter(
            ColorScheme.mood_label == analysis.mood_label
        ).first()
        
        return {
            "id": message.id,
            "text": message.text,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "mood_label": analysis.mood_label,
            "mood_score": analysis.mood_score,
            "valence": analysis.valence,
            "arousal": analysis.arousal,
            "color": {
                "primary": color.primary_color if color else "#A9A9A9",
                "secondary": color.secondary_color if color else "#D3D3D3",
                "bg": color.bg_color if color else "#F5F5F5"
            } if color else None
        }
        
    except Exception as e:
        print(f"Ошибка при получении записи {entry_id}: {e}")
        return None
        
    finally:
        if own_session:
            db.close()

def delete_entry_by_id(entry_id: int) -> dict:
    """
    Удаляет запись (сообщение и связанный с ним анализ) по ID сообщения.
    
    Параметры:
    - entry_id: ID сообщения (messages.id)
    
    Возвращает:
    - Словарь с результатом операции
    """
    db = SessionLocal()
    try:
        # Ищем сообщение по ID
        message = db.query(Message).filter(Message.id == entry_id).first()
        
        if not message:
            return {
                "success": False,
                "error": f"Запись с ID {entry_id} не найдена"
            }
        
        # Удаляем сообщение (анализ удалится автоматически благодаря cascade)
        db.delete(message)
        db.commit()
        
        return {
            "success": True,
            "message": f"Запись с ID {entry_id} успешно удалена"
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()