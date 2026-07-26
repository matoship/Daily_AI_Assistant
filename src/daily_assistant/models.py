from pydantic import BaseModel, Field
from datetime import datetime
class Article(BaseModel):
    url:str
    source:str
    title:str
    published_at:datetime | None = None
    summary:str

class TriageResult(BaseModel):
    relevance: int = Field(..., ge=0, le=10)
    category: str
    reason: str
    story_hint: str
    
class Source(BaseModel):
    url: str
    name: str
    justification: str