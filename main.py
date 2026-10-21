import os
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from supabase import create_client

from models import TimetableRequest
from solver import explain_problem, generate_timetable
from pdf_generator import create_timetable_pdf

app = FastAPI(title="Timetable Generator API")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://timetablepro.pro",
        "https://www.timetablepro.pro",
        "https://techvireon.github.io",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SavedTimetableRequest(BaseModel):
    schedule: Dict[str, Any]
    days: int
    periods_per_day: int
    layout: str = "horizontal"
    start_time: str = "08:00"
    period_length: int = 40
    period_length_after: Optional[int] = None
    break_enabled: bool = True
    break_after: int = 4
    break_length: int = 30
    campus_name: Optional[str] = None


def _pdf_headers(class_name):
    safe_name = quote(f"{class_name}_timetable.pdf")
    return {"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}


def _prepare(request):
    classes_data = {cls: [s.dict() for s in subs] for cls, subs in request.classes.items()}
    class_timing = {cls: t.dict() for cls, t in request.class_timing.items()}
    return classes_data, class_timing


@app.post("/generate-timetable")
def generate(request: TimetableRequest):
    classes_data, class_timing = _prepare(request)
    result = generate_timetable(classes_data, request.days, request.periods_per_day, class_timing)
        if result is None:
        raise HTTPException(
            status_code=400,
            detail=explain_problem(classes_data, request.days, request.periods_per_day, class_timing),
        )
    return {"timetable": result}


@app.post("/download-pdf/{class_name}")
def download_pdf(class_name: str, request: TimetableRequest):
    classes_data, class_timing = _prepare(request)
    result = generate_timetable(classes_data, request.days, request.periods_per_day, class_timing)
    if result is None or class_name not in result:
        raise HTTPException(status_code=400, detail="No timetable found for this class")

    timing = class_timing.get(class_name) or {}
    pdf = create_timetable_pdf(
        class_name,
        result[class_name],
        request.days,
        request.periods_per_day,
        start_time=timing.get("start_time", "08:00"),
        period_length=timing.get("period_length", 40),
        period_length_after=timing.get("period_length_after"),
        break_enabled=timing.get("break_enabled", True),
        break_after=timing.get("break_after", 4),
        break_length=timing.get("break_length", 30),
    )
    return StreamingResponse(pdf, media_type="application/pdf", headers=_pdf_headers(class_name))


@app.post("/download-saved-pdf/{class_name}")
def download_saved_pdf(class_name: str, request: SavedTimetableRequest):
    schedule = {}
    for day_str, periods in request.schedule.items():
        day = int(day_str)
        schedule[day] = {}
        for period_str, cell in periods.items():
            schedule[day][int(period_str)] = cell

    pdf = create_timetable_pdf(
        class_name,
        schedule,
        request.days,
        request.periods_per_day,
        start_time=request.start_time,
        period_length=request.period_length,
        period_length_after=request.period_length_after,
        break_enabled=request.break_enabled,
        break_after=request.break_after,
        break_length=request.break_length,
        layout=request.layout,
        campus_name=request.campus_name,
    )
    return StreamingResponse(pdf, media_type="application/pdf", headers=_pdf_headers(class_name))


@app.get("/test-db")
def test_db():
    if supabase is None:
        return {"connected": False}
    supabase.table("schools").select("id").limit(1).execute()
    return {"connected": True}


@app.get("/")
def root():
    return {"status": "Timetable Generator API is running"}