from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

class ParseTextRequest(BaseModel):
    text: str

class ParseResult(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    major: Optional[str] = None


class ParseTextResponse(BaseModel):
    raw_text: str
    parsed: ParseResult
    confidence: float

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/echo")
def echo(data: dict):
    return {
        "you_sent": data,
        "length": len(data)
    }

@app.post("/parse-text", response_model=ParseTextResponse)
def parse_text(payload: ParseTextRequest):
    text = payload.text
    parts = text.split()

    result = {}
    confidence = 0.0

    if len(parts) >= 1:
        result["name"] = parts[0]
        confidence += 0.25

    for p in parts:
        if p.isdigit() and "age" not in result:
            result["age"] = int(p)
            confidence += 0.25
        
    if "Beijing" in parts:
        result["city"] = "Beijing"
        confidence += 0.25

    if "Software-Engineering" in parts:
        result["major"] = "Software Engineering"
        confidence += 0.25

    return {
        "raw_text": text,
        "parsed": result,
        "confidence": round(confidence, 2)
    }