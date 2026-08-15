from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from models import TimetableRequest
from solver import generate_timetable
from pdf_generator import create_timetable_pdf
from supabase import create_client

app = FastAPI(title="Timetable Generator API")

import os

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later, change * to your real website address
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate-timetable")
def generate(request: TimetableRequest):
    classes_data = {cls: [s.dict() for s in subs] for cls, subs in request.classes.items()}
    result = generate_timetable(classes_data, request.days, request.periods_per_day)
    if result is None:
        raise HTTPException(status_code=400, detail="Could not build a timetable. Try fewer periods or more free slots.")
    return {"timetable": result}

@app.post("/download-pdf/{class_name}")
def download_pdf(class_name: str, request: TimetableRequest):
    classes_data = {cls: [s.dict() for s in subs] for cls, subs in request.classes.items()}
    result = generate_timetable(classes_data, request.days, request.periods_per_day)
    if result is None or class_name not in result:
        raise HTTPException(status_code=400, detail="No timetable found for this class")
    pdf = create_timetable_pdf(class_name, result[class_name], request.days, request.periods_per_day)
    return StreamingResponse(pdf, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={class_name}_timetable.pdf"})

@app.get("/")
def root():
    return {"status": "Timetable Generator API is running"}

@app.get("/test-db")
def test_db():
    result = supabase.table("schools").select("*").execute()
    return {"connected": True, "data": result.data}
