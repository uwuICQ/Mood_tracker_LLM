import json
from pathlib import Path
from collections import Counter
import pymorphy3

# Загрузка словаря эмоций
EMOTION_DICT_PATH = Path(__file__).parent / "emotion_dict.json"
with open(EMOTION_DICT_PATH, "r", encoding="utf-8") as f:
    EMOTION_DICT = json.load(f)

# Инициализация морфологического анализатора
morph = pymorphy3.MorphAnalyzer()

# Заранее лемматизируем все слова в словаре эмоций
LEMMED_DICT = {}
for emotion, words in EMOTION_DICT.items():
    lemmas = set()
    for w in words:
        try:
            lemma = morph.parse(w)[0].normal_form
            lemmas.add(lemma)
        except:
            lemmas.add(w.lower())
    LEMMED_DICT[emotion] = lemmas

def analyze_text(text: str) -> dict:
    """
    Анализирует текст: возвращает доминирующую эмоцию, словарь всех эмоций с интенсивностью.
    """
    text = text.lower()
    for punct in ".,!?;:()[]{}«»\"'":
        text = text.replace(punct, " ")
    words = text.split()
    if not words:
        return {
            "dominant_emotion": "neutral",
            "emotions": {"neutral": 1.0},
            "intensity": 0.0
        }
    
    # Лемматизация слов текста
    text_lemmas = []
    for w in words:
        try:
            lemma = morph.parse(w)[0].normal_form
            text_lemmas.append(lemma)
        except:
            text_lemmas.append(w)
    
    if not text_lemmas:
        return {
            "dominant_emotion": "neutral",
            "emotions": {"neutral": 1.0},
            "intensity": 0.0
        }
    
    # Подсчёт баллов для каждой эмоции
    emotion_scores = Counter()
    for lemma in text_lemmas:
        for emotion, lemma_set in LEMMED_DICT.items():
            if lemma in lemma_set:
                emotion_scores[emotion] += 1
    
    if not emotion_scores:
        return {
            "dominant_emotion": "neutral",
            "emotions": {"neutral": 1.0},
            "intensity": 0.0
        }
    
    # Преобразуем счётчики в интенсивности (доля от общего числа лемм)
    total = len(text_lemmas)
    emotion_intensities = {}
    for em, count in emotion_scores.items():
        emotion_intensities[em] = round(count / total, 2)
    
    # Доминирующая эмоция – с максимальной интенсивностью
    dominant = max(emotion_intensities.items(), key=lambda x: x[1])
    
    return {
        "dominant_emotion": dominant[0],
        "emotions": emotion_intensities,
        "intensity": dominant[1]
    }

def emotion_to_rgb(emotion: str, intensity: float) -> tuple:
    """Возвращает RGB-цвет для одной эмоции с учётом интенсивности (оставлено для совместимости)."""
    base_colors = {
        "joy": (255, 223, 0),
        "sadness": (70, 70, 150),
        "anger": (200, 0, 0),
        "fear": (80, 0, 80),
        "surprise": (0, 150, 200),
        "love": (255, 105, 180),
        "calm": (100, 200, 100),
        "trust": (50, 150, 150),
        "disgust": (100, 50, 0),
        "anticipation": (255, 140, 0),
        "shame": (180, 100, 100),
        "jealousy": (34, 139, 34),
        "hope": (255, 215, 0),
        "loneliness": (105, 105, 105),
        "gratitude": (255, 215, 150),
        "neutral": (240, 240, 240)
    }
    r0, g0, b0 = base_colors.get(emotion, (200, 200, 200))
    neutral = (240, 240, 240)
    r = int(r0 * intensity + neutral[0] * (1 - intensity))
    g = int(g0 * intensity + neutral[1] * (1 - intensity))
    b = int(b0 * intensity + neutral[2] * (1 - intensity))
    return (r, g, b)

def mix_colors(emotions_intensities: dict) -> tuple:
    """
    Смешивает цвета эмоций пропорционально их интенсивности.
    emotions_intensities: {'joy': 0.3, 'sadness': 0.7, ...}
    """
    if not emotions_intensities:
        return (240, 240, 240)
    
    base_colors = {
        "joy": (255, 223, 0),
        "sadness": (70, 70, 150),
        "anger": (200, 0, 0),
        "fear": (80, 0, 80),
        "surprise": (0, 150, 200),
        "love": (255, 105, 180),
        "calm": (100, 200, 100),
        "trust": (50, 150, 150),
        "disgust": (100, 50, 0),
        "anticipation": (255, 140, 0),
        "shame": (180, 100, 100),
        "jealousy": (34, 139, 34),
        "hope": (255, 215, 0),
        "loneliness": (105, 105, 105),
        "gratitude": (255, 215, 150),
        "neutral": (240, 240, 240)
    }
    
    total_intensity = sum(emotions_intensities.values())
    if total_intensity == 0:
        return (240, 240, 240)
    
    r = g = b = 0
    for emotion, intensity in emotions_intensities.items():
        weight = intensity / total_intensity
        color = base_colors.get(emotion, (200, 200, 200))
        r += color[0] * weight
        g += color[1] * weight
        b += color[2] * weight
    
    return (int(r), int(g), int(b))