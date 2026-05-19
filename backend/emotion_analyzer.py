import json
from pathlib import Path
from collections import Counter
import difflib
import pymorphy3

# ---------- Загрузка словаря эмоций ----------
EMOTION_DICT_PATH = Path(__file__).parent / "emotion_dict.json"
with open(EMOTION_DICT_PATH, "r", encoding="utf-8") as f:
    EMOTION_DICT = json.load(f)

# ---------- Лемматизатор ----------
morph = pymorphy3.MorphAnalyzer()

# ---------- База эмоций (леммы) ----------
EMOTION_LEMMAS = {}  # lemma -> emotion
for emotion, words in EMOTION_DICT.items():
    for w in words:
        try:
            lemma = morph.parse(w)[0].normal_form
            EMOTION_LEMMAS[lemma] = emotion
        except:
            EMOTION_LEMMAS[w] = emotion

# ---------- Загрузка валидных русских слов ----------
WORDLIST_PATH = Path(__file__).parent / "100_000_russian_wordlist.txt"
VALID_RUSSIAN_WORDS = set()
if WORDLIST_PATH.exists():
    with open(WORDLIST_PATH, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip().lower()
            if word:
                VALID_RUSSIAN_WORDS.add(word)
    print(f"✅ Загружено корректных слов: {len(VALID_RUSSIAN_WORDS)}")
else:
    print("⚠️ Файл с русскими словами не найден, исправление опечаток отключено")

# Добавляем в валидные все эмоциональные леммы (чтобы их не исправлять)
VALID_RUSSIAN_WORDS.update(EMOTION_LEMMAS.keys())

# ---------- Ручной словарь частых опечаток (добавляйте по мере необходимости) ----------
MANUAL_TYPOS = {
    "звидую": "завидую",
    "звидовать": "завидовать",
    "плчу": "плачу",
    "плчю": "плачу",
    "радось": "радость",
    "счаслив": "счастлив",
    "подруга": "подруга",  # явно говорим, что это правильное слово
    "крутая": "крутая",
}

def fix_typo(word: str) -> str:
    """Исправляет опечатку, только если слово не найдено в словаре правильных слов."""
    # 1. Если слово есть в ручном словаре – сразу заменяем
    if word in MANUAL_TYPOS:
        return MANUAL_TYPOS[word]
    
    # 2. Если слово уже есть в списке правильных – не трогаем
    if word in VALID_RUSSIAN_WORDS:
        return word
    
    # 3. Пытаемся найти очень похожее слово (порог 0.85) среди эмоциональных лемм
    # Это снизит риск ложных замен (например, 'крутая' не похожа на 'круто' на 0.85)
    matches = difflib.get_close_matches(word, EMOTION_LEMMAS.keys(), n=1, cutoff=0.85)
    if matches:
        return matches[0]  # возвращаем исправленную лемму
    
    # 4. Иначе пытаемся найти похожее слово во всём словаре правильных слов (порог 0.9)
    matches = difflib.get_close_matches(word, VALID_RUSSIAN_WORDS, n=1, cutoff=0.9)
    if matches:
        return matches[0]
    
    # 5. Ничего не нашли – оставляем как есть
    return word

def analyze_text(text: str) -> dict:
    text = text.lower()
    for punct in ".,!?;:()[]{}«»\"'":
        text = text.replace(punct, " ")
    words = text.split()

    if not words:
        return {"dominant_emotion": "neutral", "emotions": {"neutral": 1.0}, "intensity": 0.0}

    emotion_scores = Counter()
    for raw_word in words:
        if len(raw_word) < 2:
            continue

        # Исправляем опечатку (только если это действительно опечатка)
        corrected = fix_typo(raw_word)
        
        # Лемматизация исправленного слова
        try:
            lemma = morph.parse(corrected)[0].normal_form
        except:
            lemma = corrected

        # Проверка эмоции
        if lemma in EMOTION_LEMMAS:
            emotion = EMOTION_LEMMAS[lemma]
            emotion_scores[emotion] += 1
            if corrected != raw_word:
                print(f"Исправлена опечатка: '{raw_word}' → '{corrected}' (лемма '{lemma}' -> {emotion})")
            else:
                print(f"Распознано слово: '{raw_word}' (лемма '{lemma}' -> {emotion})")
        else:
            # Для отладки: выводим слова, которые не дали эмоции
            if raw_word not in VALID_RUSSIAN_WORDS:
                print(f"Неизвестное слово: '{raw_word}' (исправлено как '{corrected}', лемма '{lemma}')")

    if not emotion_scores:
        return {"dominant_emotion": "neutral", "emotions": {"neutral": 1.0}, "intensity": 0.0}

    total = sum(emotion_scores.values())
    intensities = {em: round(cnt / total, 2) for em, cnt in emotion_scores.items()}
    dominant = max(intensities.items(), key=lambda x: x[1])

    return {
        "dominant_emotion": dominant[0],
        "emotions": intensities,
        "intensity": dominant[1]
    }

# ---------- Функции цвета (оставляем как есть) ----------
def emotion_to_rgb(emotion: str, intensity: float) -> tuple:
    base = {
        "joy": (255, 223, 0), "sadness": (70, 70, 150), "anger": (200, 0, 0),
        "fear": (80, 0, 80), "surprise": (0, 150, 200), "love": (255, 105, 180),
        "calm": (100, 200, 100), "trust": (50, 150, 150), "disgust": (100, 50, 0),
        "anticipation": (255, 140, 0), "shame": (180, 100, 100), "jealousy": (34, 139, 34),
        "hope": (255, 215, 0), "loneliness": (105, 105, 105), "gratitude": (255, 215, 150),
        "neutral": (240, 240, 240)
    }
    r0, g0, b0 = base.get(emotion, (200, 200, 200))
    neutral = (240, 240, 240)
    r = int(r0 * intensity + neutral[0] * (1 - intensity))
    g = int(g0 * intensity + neutral[1] * (1 - intensity))
    b = int(b0 * intensity + neutral[2] * (1 - intensity))
    return (r, g, b)

def mix_colors(emotions_intensities: dict) -> tuple:
    if not emotions_intensities:
        return (240, 240, 240)
    base = {
        "joy": (255, 223, 0), "sadness": (70, 70, 150), "anger": (200, 0, 0),
        "fear": (80, 0, 80), "surprise": (0, 150, 200), "love": (255, 105, 180),
        "calm": (100, 200, 100), "trust": (50, 150, 150), "disgust": (100, 50, 0),
        "anticipation": (255, 140, 0), "shame": (180, 100, 100), "jealousy": (34, 139, 34),
        "hope": (255, 215, 0), "loneliness": (105, 105, 105), "gratitude": (255, 215, 150),
        "neutral": (240, 240, 240)
    }
    total = sum(emotions_intensities.values())
    if total == 0:
        return (240, 240, 240)
    r = g = b = 0
    for em, intens in emotions_intensities.items():
        weight = intens / total
        col = base.get(em, (200, 200, 200))
        r += col[0] * weight
        g += col[1] * weight
        b += col[2] * weight
    return (int(r), int(g), int(b))