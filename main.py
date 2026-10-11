import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from supabase import create_client

from models import TimetableRequest
from solver import generate_timetable
from pdf_generator import create_timetable_pdf

app = FastAPI(title="Timetable Generator API")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later, change * to your real website address
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


@app.post("/generate-timetable")
def generate(request: TimetableRequest):
    classes_data = {cls: [s.dict() for s in subs] for cls, subs in request.classes.items()}
    result = generate_timetable(classes_data, request.days, request.periods_per_day)
    if result is None:
        raise HTTPException(
            status_code=400,
            detail="Could not build a timetable. Try fewer periods or more free slots.",
        )
    return {"timetable": result}


@app.post("/download-pdf/{class_name}")
def download_pdf(class_name: str, request: TimetableRequest):
    classes_data = {cls: [s.dict() for s in subs] for cls, subs in request.classes.items()}
    result = generate_timetable(classes_data, request.days, request.periods_per_day)
    if result is None or class_name not in result:
        raise HTTPException(status_code=400, detail="No timetable found for this class")
    pdf = create_timetable_pdf(class_name, result[class_name], request.days, request.periods_per_day)
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{class_name}_timetable.pdf"'},
    )


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
    )
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{class_name}_timetable.pdf"'},
    )


@app.get("/test-db")
def test_db():
    result = supabase.table("schools").select("*").execute()
    return {"connected": True, "data": result.data}


@app.get("/")
def root():
    return {"status": "Timetable Generator API is running"}