import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from openai import OpenAI
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

class ParsedPdfResponse(BaseModel):
    pages: int
    preview_text: str

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise RuntimeError("DEEPSEEK_API_KEY not set")

client = OpenAI(
    api_key = api_key,
    base_url = "https://api.deepseek.com"
)

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

    result = ParseResult()
    confidence = 0.0

    if len(parts) >= 1:
        result.name = parts[0]
        confidence += 0.25

    for p in parts:
        if p.isdigit() and result.age is None:
            result.age = int(p)
            confidence += 0.25
        
    if "Beijing" in parts:
        result.city = "Beijing"
        confidence += 0.25

    if "Software-Engineering" in parts:
        result.major = "Software Engineering"
        confidence += 0.25

    return ParseTextResponse(
        raw_text = text,
        parsed = result,
        confidence = round(confidence, 2)
    )

@app.post("/parse-pdf", response_model=ParsedPdfResponse)
def parse_pdf(file: UploadFile = File(...)):
    import pymupdf

    doc = pymupdf.open(stream=file.file.read(), filetype="pdf")

    preview_lines = []
    for page in doc[:2]: # select first 2 pages
        text = page.get_text()
        preview_lines.extend(text.splitlines())

    preview = "\n".join(preview_lines[:20])
    
    return ParsedPdfResponse(
        pages=doc.page_count,
        preview_text=preview
    )

def ai_parse(text: str) -> dict:
    PROMPT = """
        Extract the following fields from the text.
        Return JSON only.

        Fields:
        - name
        - age
        - city
        - major

        Text:
        {text}
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are a JSON generator.\n"
                    "You must output valid strict JSON only.\n"
                    "Do not include markdown, comments, or extra text."
                )
            },
            {
                "role": "user",
                "content": PROMPT.format(text = text)
            },
        ]
    )

    content = response.choices[0].message.content
    print(content)

    return json.loads(content)

@app.post("/ai/parse-text", response_model=ParseResult)
def ai_parse_text(payload: ParseTextRequest):
    result = ai_parse(payload.text)
    return ParseResult(**result)