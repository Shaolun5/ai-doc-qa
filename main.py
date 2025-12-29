from fastapi import FastAPI
from typing import Optional

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

@app.post("/parse-text")
def parse_text(payload: dict):
    text = payload.get("text", "")
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