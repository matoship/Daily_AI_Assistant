from pydantic import BaseModel
from datetime import datetime

class Article(BaseModel):
    url:str
    source:str
    title:str
    published_at:datetime | None = None
    summary:str