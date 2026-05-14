from fastapi import FastAPI
from pydantic import BaseModel, Field
from emotion_analyzer import analyze_text, mix_colors

app = FastAPI(title="Emotion Analyzer API", version="1.0.0")

class TextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)

class AnalyzeResponse(BaseModel):
    emotion: str
    intensity: float
    color: str

@app.get("/")
def root():
    return {"message": "Emotion Analyzer API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: TextRequest):
    result = analyze_text(request.text)
    mixed_rgb = mix_colors(result["emotions"])
    color_hex = f"#{mixed_rgb[0]:02x}{mixed_rgb[1]:02x}{mixed_rgb[2]:02x}"
    return AnalyzeResponse(
        emotion=result["dominant_emotion"],
        intensity=result["intensity"],
        color=color_hex
    )