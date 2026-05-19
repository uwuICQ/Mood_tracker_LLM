from fastapi import FastAPI, Body, HTTPException
from typing import List
from datetime import datetime
from pathlib import Path

from emotion_analyzer import analyze_text, mix_colors, emotion_to_rgb

app = FastAPI(title="Emotion Analyzer API", version="1.0.0")

# Путь к логам
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "emotion_log.txt"

def log_to_file(text: str, all_emotions: list, final_color: str):
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emotions_str = ", ".join([f"{e['emotion']}:{e['intensity']}" for e in all_emotions])
    log_entry = f"[{timestamp}] Текст: {text} | Эмоции: {emotions_str} | Итоговый цвет: {final_color}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

@app.get("/")
def root():
    return {"message": "Emotion Analyzer API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze")
def analyze(text: str = Body(..., media_type="text/plain", max_length=1000)):
    """
    Принимает текст в виде обычной строки (Content-Type: text/plain).
    Максимальная длина 1000 символов.
    """
    # Проверка длины (на случай, если FastAPI не обрезает)
    if len(text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long, maximum 1000 characters")

    # Анализ текста
    result = analyze_text(text)

    # Смешиваем цвета
    mixed_rgb = mix_colors(result["emotions"])
    color_hex = f"#{mixed_rgb[0]:02x}{mixed_rgb[1]:02x}{mixed_rgb[2]:02x}"

    # Формируем список эмоций
    all_emotions = []
    for emotion, intensity in result["emotions"].items():
        rgb = emotion_to_rgb(emotion, intensity)
        emotion_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        all_emotions.append({
            "emotion": emotion,
            "intensity": intensity,
            "color": emotion_color
        })

    # Логирование
    print(f"\n=== Анализ текста ===")
    print(f"Текст: {text}")
    print(f"Обнаруженные эмоции: {[(e['emotion'], e['intensity']) for e in all_emotions]}")
    print(f"Итоговый цвет: {color_hex}")
    print("=====================\n")

    log_to_file(text, all_emotions, color_hex)

    return {
        "emotion": result["dominant_emotion"],
        "intensity": result["intensity"],
        "color": color_hex,
        "all_emotions": all_emotions
    }