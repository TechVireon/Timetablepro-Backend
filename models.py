from pydantic import BaseModel
from typing import List, Dict

class SubjectEntry(BaseModel):
    subject: str
    teacher: str
    periods_per_week: int

class TimetableRequest(BaseModel):
    days: int = 5
    periods_per_day: int = 7
    classes: Dict[str, List[SubjectEntry]]