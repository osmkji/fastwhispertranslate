from pydantic import BaseModel
from typing import List, Optional

class Word(BaseModel):
    start: float
    end: float
    word: str

class Segment(BaseModel):
    start: float
    end: float
    text: str
    words: Optional[List[Word]] = []

class TranscriptionResponse(BaseModel):
    language: str
    duration: float
    segments: List[Segment]
