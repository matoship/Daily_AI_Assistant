from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal
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
    
class DigestItem(BaseModel):
    headline: str
    summary: str
    why_it_matters: str
    category: str
    article_urls: list[str]

ArticleStatus = Literal["fetched", "scored", "digested", "outdated"]
