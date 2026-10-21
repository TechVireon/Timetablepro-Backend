from typing import Dict, List, Optional

from pydantic import BaseModel


class SubjectEntry(BaseModel):
    subject: str
    teacher: str
    periods_per_week: int


class TimingEntry(BaseModel):
    start_time: str = "08:00"
    period_length: int = 40
    period_length_after: Optional[int] = None
    break_enabled: bool = True
    break_after: int = 4
    break_length: int = 30


class TimetableRequest(BaseModel):
    days: int = 5
    periods_per_day: int = 7
    classes: Dict[str, List[SubjectEntry]]
    class_timing: Dict[str, TimingEntry] = {}