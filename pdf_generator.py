from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

DAY_NAMES = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


def _format_time(total_minutes):
    h = (total_minutes // 60) % 24
    m = total_minutes % 60
    ampm = "PM" if h >= 12 else "AM"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{m:02d} {ampm}"


def _build_timeline(start_time, period_length, break_after, break_length, total_periods):
    try:
        hour, minute = start_time.split(":")[:2]
        current = int(hour) * 60 + int(minute)
    except Exception:
        current = 8 * 60

    timeline = []
    for p in range(1, total_periods + 1):
        start = current
        end = current + period_length
        timeline.append({
            "period": p,
            "is_break": False,
            "label": f"{_format_time(start)} - {_format_time(end)}",
        })
        current = end
        if p == break_after:
            break_end = current + break_length
            timeline.append({
                "period": None,
                "is_break": True,
                "label": f"Break\n{_format_time(current)} - {_format_time(break_end)}",
            })
            current = break_end
    return timeline


def create_timetable_pdf(class_name, class_schedule, days=5, periods_per_day=7,
                         start_time="08:00", period_length=40,
                         break_after=4, break_length=30):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Timetable - {class_name}", styles["Title"]), Spacer(1, 12)]

    timeline = _build_timeline(start_time, period_length, break_after, break_length, periods_per_day)

    data = [["Time"] + [DAY_NAMES[d] for d in range(days)]]
    break_rows = []

    for slot in timeline:
        row_index = len(data)
        if slot["is_break"]:
            data.append([slot["label"]] + ["-"] * days)
            break_rows.append(row_index)
        else:
            row = [slot["label"]]
            for d in range(days):
                cell = class_schedule.get(d, {}).get(slot["period"] - 1)
                row.append(f"{cell['subject']}\n{cell['teacher']}" if cell else "-")
            data.append(row)

    first_col = 120
    other_col = (770 - first_col) / days
    table = Table(data, colWidths=[first_col] + [other_col] * days, repeatRows=1)

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3B7BF2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#EFF6FF")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for r in break_rows:
        style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F3F4F6")))
        style.append(("TEXTCOLOR", (0, r), (-1, r), colors.HexColor("#9CA3AF")))
        style.append(("FONTNAME", (0, r), (-1, r), "Helvetica-Oblique"))

    table.setStyle(TableStyle(style))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer