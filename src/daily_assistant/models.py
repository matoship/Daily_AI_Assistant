from pydantic import BaseModel
from datetime import datetime

class Article(BaseModel):
    url:str
    source:str
    title:str
    published_at:datetime | None = None
    summary:str

class TriageResult(BaseModel):
    relevance: int
    category: str
    reason: str
    story_hint: str
    
class Source(BaseModel):
    url: str
    name: str
    justification: str