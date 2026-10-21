from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DAY_NAMES = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

HEADER_BLUE = colors.HexColor("#3B7BF2")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
GRID_GRAY = colors.HexColor("#D1D5DB")
BREAK_BG = colors.HexColor("#F3F4F6")
BREAK_TEXT = colors.HexColor("#9CA3AF")


def _format_time(total_minutes):
    h = (total_minutes // 60) % 24
    m = total_minutes % 60
    ampm = "PM" if h >= 12 else "AM"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{m:02d} {ampm}"


def _build_timeline(start_time, period_length, period_length_after,
                    break_enabled, break_after, break_length, total_periods):
    try:
        hour, minute = start_time.split(":")[:2]
        current = int(hour) * 60 + int(minute)
    except Exception:
        current = 8 * 60

    timeline = []
    for p in range(1, total_periods + 1):
        length = period_length_after if (break_enabled and p > break_after) else period_length
        start = current
        end = current + length
        timeline.append({
            "period": p,
            "is_break": False,
            "start": _format_time(start),
            "end": _format_time(end),
        })
        current = end

        if break_enabled and p == break_after:
            break_end = current + break_length
            timeline.append({
                "period": None,
                "is_break": True,
                "start": _format_time(current),
                "end": _format_time(break_end),
            })
            current = break_end
    return timeline


def _cell_text(class_schedule, day, slot):
    cell = class_schedule.get(day, {}).get(slot["period"] - 1)
    if cell:
        return f"{cell['subject']}\n{cell['teacher']}"
    return "-"


def create_timetable_pdf(class_name, class_schedule, days=5, periods_per_day=7,
                         start_time="08:00", period_length=40,
                         period_length_after=None, break_enabled=True,
                         break_after=4, break_length=30, layout="horizontal",
                         campus_name=None):
    if period_length_after is None:
        period_length_after = period_length

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    campus_style = ParagraphStyle("CampusLine", parent=styles["Heading3"], alignment=1)

    elements = [Paragraph(f"Timetable - {escape(class_name)}", styles["Title"])]
    if campus_name:
        elements.append(Paragraph(f"Campus: {escape(campus_name)}", campus_style))
    elements.append(Spacer(1, 12))

    timeline = _build_timeline(
        start_time, period_length, period_length_after,
        break_enabled, break_after, break_length, periods_per_day,
    )

    usable_width = 770
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (0, -1), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID_GRAY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    if layout == "vertical":
        header = ["Day"]
        for slot in timeline:
            if slot["is_break"]:
                header.append(f"Break\n{slot['start']} -\n{slot['end']}")
            else:
                header.append(f"{slot['start']} -\n{slot['end']}")
        data = [header]

        for d in range(days):
            row = [DAY_NAMES[d]]
            for slot in timeline:
                row.append("-" if slot["is_break"] else _cell_text(class_schedule, d, slot))
            data.append(row)

        first_col = 50
        other_col = (usable_width - first_col) / len(timeline)
        col_widths = [first_col] + [other_col] * len(timeline)
        font_size = 8 if len(timeline) <= 9 else 7
        style.append(("FONTSIZE", (0, 0), (-1, -1), font_size))

        for i, slot in enumerate(timeline):
            if slot["is_break"]:
                c = i + 1
                style.append(("BACKGROUND", (c, 0), (c, 0), BREAK_TEXT))
                style.append(("BACKGROUND", (c, 1), (c, -1), BREAK_BG))
                style.append(("TEXTCOLOR", (c, 1), (c, -1), BREAK_TEXT))
    else:
        data = [["Time"] + [DAY_NAMES[d] for d in range(days)]]
        break_rows = []

        for slot in timeline:
            if slot["is_break"]:
                data.append([f"Break\n{slot['start']} - {slot['end']}"] + ["-"] * days)
                break_rows.append(len(data) - 1)
            else:
                row = [f"{slot['start']} - {slot['end']}"]
                for d in range(days):
                    row.append(_cell_text(class_schedule, d, slot))
                data.append(row)

        first_col = 120
        other_col = (usable_width - first_col) / days
        col_widths = [first_col] + [other_col] * days
        style.append(("FONTSIZE", (0, 0), (-1, -1), 9))

        for r in break_rows:
            style.append(("BACKGROUND", (0, r), (-1, r), BREAK_BG))
            style.append(("TEXTCOLOR", (0, r), (-1, r), BREAK_TEXT))
            style.append(("FONTNAME", (0, r), (-1, r), "Helvetica-Oblique"))

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle(style))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer