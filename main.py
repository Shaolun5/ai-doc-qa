from dataclasses import dataclass
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from openai import OpenAI
from pydantic import BaseModel
from typing import Literal, Optional

class ParseTextRequest(BaseModel):
    text: str

class ParseResult(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    major: Optional[str] = None
    source: Literal["rule", "ai", "fallback"]
    confidence: float

class ParseTextResponse(BaseModel):
    raw_text: str
    parsed: ParseResult

class ParsePdfPreviewResponse(BaseModel):
    pages: int
    preview_text: str

@dataclass
class TextChunk:
    doc_id: str
    chunk_id: int
    text: str

class ParsedPdfResponse(BaseModel):
    number_of_chunks: int
    chunk_1: Optional[TextChunk] = None
    chunk_2: Optional[TextChunk] = None
    chunk_last: Optional[TextChunk] = None

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

def rule_based_parse(text: str) -> ParseResult:
    parts = text.split()

    result = ParseResult(source="rule", confidence=0.0)

    if len(parts) >= 1:
        result.name = parts[0]
        result.confidence += 0.25

    for p in parts:
        if p.isdigit() and result.age is None:
            result.age = int(p)
            result.confidence += 0.25
        
    if "Beijing" in parts:
        result.city = "Beijing"
        result.confidence += 0.25

    if "Software-Engineering" in parts:
        result.major = "Software Engineering"
        result.confidence += 0.25

    result.confidence = round(result.confidence, 2)
    return result

@app.post("/parse-text", response_model=ParseTextResponse)
def parse_text(payload: ParseTextRequest):
    result = rule_based_parse(payload.text)

    return ParseTextResponse(
        raw_text = payload.text,
        parsed = result,
    )

@app.post("/parse-pdf-preview", response_model=ParsePdfPreviewResponse)
def parse_pdf_preview(file: UploadFile = File(...)):
    import pymupdf

    with pymupdf.open(stream=file.file.read(), filetype="pdf") as doc:
        preview_lines = []
        for page in doc[:2]: # select first 2 pages
            text = page.get_text()
            preview_lines.extend(text.splitlines())

        preview = "\n".join(preview_lines[:20])
        
        return ParsePdfPreviewResponse(
            pages=doc.page_count,
            preview_text=preview
        )

def ai_parse(text: str) -> dict:
    PROMPT = f"""
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
                "content": PROMPT
            },
        ]
    )

    content = response.choices[0].message.content
    print(content)

    return json.loads(content)

@app.post("/ai/parse-text", response_model=ParseResult)
def ai_parse_text(payload: ParseTextRequest):
    try:
        result = ai_parse(payload.text)
        return ParseResult(
            **result,
            source="ai",
            confidence=0.8
        )
    except Exception:
        rule_result = rule_based_parse(payload.text)
        rule_result.source = "fallback"
        return rule_result
    

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    '''
    A fixed size chunking function
    It breaks down the text into chunks of specified number of characters, which is
    passed in by chunk_size.
    '''
    if chunk_size <= overlap:
        raise ValueError

    chunk_li = []

    for i in range(0, len(text), chunk_size - overlap):
        chunk_li.append(text[i:i+chunk_size])

    return chunk_li

def build_chunks(text: str, doc_id: str) -> list[TextChunk]:
    chunks = []
    raw_chunks = chunk_text(text)
    
    for i in range(len(raw_chunks)):
        chunks.append(TextChunk(doc_id, i, raw_chunks[i]))

    return chunks

@app.post("/parse-pdf", response_model=ParsedPdfResponse)
def parse_pdf(file: UploadFile = File(...)):
    import pymupdf

    with pymupdf.open(stream=file.file.read(), filetype="pdf") as doc:
        lines = []
        for page in doc: # select first 2 pages
            lines.extend(page.get_text().splitlines())

        text = '\n'.join(lines)

        chunks = build_chunks(text, file.filename)
        n = len(chunks)

        preview = ParsedPdfResponse(number_of_chunks=n)
        if n > 0:
            preview.chunk_1 = chunks[0]
            preview.chunk_last = chunks[-1]
        if n > 1:
            preview.chunk_2 = chunks[1]

        return preview