from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List
from pathlib import Path
from datetime import datetime

from emotion_analyzer import analyze_text, mix_colors, emotion_to_rgb, get_supportive_message

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ---------- База данных ----------
DATABASE_URL = "sqlite:///./data/emotions.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EntryDB(Base):
    __tablename__ = "entries"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    emotion = Column(String, nullable=False)
    intensity = Column(Float, nullable=False)
    color = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ---------- Pydantic ----------
class TextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)

class EmotionDetail(BaseModel):
    emotion: str
    intensity: float
    color: str

class AnalyzeResponse(BaseModel):
    emotion: str
    intensity: float
    color: str
    all_emotions: List[EmotionDetail] = []
    supportive_message: str   # добавлено поле с поддерживающей фразой

class EntryResponse(BaseModel):
    id: int
    text: str
    emotion: str
    intensity: float
    color: str
    timestamp: str

# ---------- FastAPI ----------
app = FastAPI(title="Emotion Analyzer API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
def root():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Emotion Analyzer API is running. Go to /docs for Swagger."}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: TextRequest, db: Session = Depends(get_db)):
    result = analyze_text(request.text)
    mixed_rgb = mix_colors(result["emotions"])
    color_hex = f"#{mixed_rgb[0]:02x}{mixed_rgb[1]:02x}{mixed_rgb[2]:02x}"
    
    all_emotions = []
    for emotion, intensity in result["emotions"].items():
        rgb = emotion_to_rgb(emotion, intensity)
        all_emotions.append(EmotionDetail(
            emotion=emotion,
            intensity=intensity,
            color=f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        ))
    
    # Получаем поддерживающую фразу для доминирующей эмоции
    supportive_msg = get_supportive_message(result["dominant_emotion"])
    
    # Сохраняем в БД
    entry = EntryDB(
        text=request.text,
        emotion=result["dominant_emotion"],
        intensity=result["intensity"],
        color=color_hex
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    
    return AnalyzeResponse(
        emotion=result["dominant_emotion"],
        intensity=result["intensity"],
        color=color_hex,
        all_emotions=all_emotions,
        supportive_message=supportive_msg
    )

@app.get("/entries", response_model=List[EntryResponse])
def get_entries(db: Session = Depends(get_db)):
    entries = db.query(EntryDB).order_by(EntryDB.timestamp.desc()).all()
    return [
        EntryResponse(
            id=e.id,
            text=e.text,
            emotion=e.emotion,
            intensity=e.intensity,
            color=e.color,
            timestamp=e.timestamp.isoformat()
        ) for e in entries
    ]

@app.delete("/entries/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(EntryDB).filter(EntryDB.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
    return {"status": "ok"}
