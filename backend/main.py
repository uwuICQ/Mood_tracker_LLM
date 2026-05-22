from fastapi import FastAPI, Body, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pathlib import Path
import httpx

from emotion_analyzer import analyze_text, mix_colors, emotion_to_rgb, get_supportive_message

app = FastAPI(title="Emotion Analyzer API", version="1.0.0")

# ---------- CORS (разрешаем запросы с фронта) ----------
# ПРОД: заменить "*" на конкретный домен фронта, например ["https://мойсайт.ru"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Конфигурация отправки логов в БД коллеги ----------
# ПРОД: заменить на реальный URL API коллеги
LOG_SERVICE_URL = "http://localhost:8080/logs"   # пример, надо будет заменить

# ---------- Логирование в файл (для отладки) ----------
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "emotion_log.txt"

def log_to_file(text: str, all_emotions: list, final_color: str):
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emotions_str = ", ".join([f"{e['emotion']}:{e['intensity']}" for e in all_emotions])
    log_entry = f"[{timestamp}] Текст: {text} | Эмоции: {emotions_str} | Итоговый цвет: {final_color}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

# ---------- Функция отправки лога в БД коллеги (асинхронная) ----------
async def send_log_to_db(log_data: dict):
    """
    Отправляет лог в API коллеги. Вызывается в фоновом режиме.
    Если сервис логов недоступен, ошибка логируется в консоль, но не ломает ответ клиенту.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(LOG_SERVICE_URL, json=log_data)
            if response.status_code >= 400:
                print(f"Ошибка при отправке лога: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Не удалось отправить лог в БД: {e}")

# ---------- Корневые эндпоинты ----------
@app.get("/")
def root():
    return {"message": "Emotion Analyzer API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

# ---------- Главный эндпоинт для анализа ----------
@app.post("/analyze")
def analyze(text: str = Body(..., media_type="text/plain", max_length=1000),
            background_tasks: BackgroundTasks = BackgroundTasks()):
    """
    Принимает текст, анализирует эмоции, возвращает результат.
    Фоново отправляет лог в БД коллеги.
    """
    if len(text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long, maximum 1000 characters")

    # Анализ эмоций
    result = analyze_text(text)

    # Смешивание цветов
    mixed_rgb = mix_colors(result["emotions"])
    color_hex = f"#{mixed_rgb[0]:02x}{mixed_rgb[1]:02x}{mixed_rgb[2]:02x}"

    # Формируем список всех эмоций для ответа
    all_emotions = []
    for emotion, intensity in result["emotions"].items():
        rgb = emotion_to_rgb(emotion, intensity)
        emotion_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        all_emotions.append({
            "emotion": emotion,
            "intensity": intensity,
            "color": emotion_color
        })

    # Поддерживающая фраза на основе доминирующей эмоции
    dominant_emotion = result["dominant_emotion"]
    supportive_message = get_supportive_message(dominant_emotion)

    # ----- Логирование -----
    # 1. Лог в файл (локально)
    log_to_file(text, all_emotions, color_hex)

    # 2. Лог в консоль (для отладки)
    print(f"\n=== Анализ текста ===")
    print(f"Текст: {text}")
    print(f"Обнаруженные эмоции: {[(e['emotion'], e['intensity']) for e in all_emotions]}")
    print(f"Итоговый цвет: {color_hex}")
    print(f"Фраза: {supportive_message}")
    print("=====================\n")

    # 3. Отправка лога в БД коллеги (фоновая задача)
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "text": text,
        "dominant_emotion": dominant_emotion,
        "intensity": result["intensity"],
        "final_color": color_hex,
        "all_emotions": all_emotions,
        "message": supportive_message
    }
    background_tasks.add_task(send_log_to_db, log_data)

    # Ответ для фронта
    return {
        "emotion": dominant_emotion,
        "intensity": result["intensity"],
        "color": color_hex,
        "all_emotions": all_emotions,
        "message": supportive_message
    }

    # Новый эндпоинт для получения случайного факта
@app.get("/random-fact")
async def random_fact():
    """
    Возвращает случайный бессмысленный факт для поднятия настроения.
    Используется публичное API uselessfacts.jsph.pl.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # API возвращает факты на английском. Можно добавить параметр ?language=ru, но русские факты не гарантированы.
            response = await client.get("https://uselessfacts.jsph.pl/random.json?language=en")
            if response.status_code == 200:
                data = response.json()
                fact = data.get("text", "Сегодня отличный день, чтобы улыбнуться!")
                return {"fact": fact}
            else:
                return {"fact": "Не удалось загрузить факт. Но помни: ты молодец!"}
    except Exception as e:
        print(f"Ошибка при получении факта: {e}")
        return {"fact": "Иногда жизнь – лучший источник неожиданных фактов. Улыбнись!"}