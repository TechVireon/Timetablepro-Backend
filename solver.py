import math
import re

from ortools.sat.python import cp_model

DEFAULT_TIMING = {
    "start_time": "08:00",
    "period_length": 40,
    "period_length_after": None,
    "break_enabled": True,
    "break_after": 4,
    "break_length": 30,
}


def _normalize_teacher(name):
    return re.sub(r"\s+", " ", str(name).strip()).lower()


def _period_times(timing, periods_per_day):
    """Start and end minute of every period, for one class."""
    t = dict(DEFAULT_TIMING)
    t.update({k: v for k, v in (timing or {}).items() if v is not None})

    try:
        hour, minute = str(t["start_time"]).split(":")[:2]
        current = int(hour) * 60 + int(minute)
    except Exception:
        current = 8 * 60

    length_before = int(t["period_length"])
    length_after = int(t["period_length_after"]) if t.get("period_length_after") else length_before
    break_on = bool(t["break_enabled"])
    break_after = int(t["break_after"])
    break_length = int(t["break_length"])

    times = []
    for p in range(1, periods_per_day + 1):
        length = length_after if (break_on and p > break_after) else length_before
        times.append((current, current + length))
        current += length
        if break_on and p == break_after:
            current += break_length
    return times


def generate_timetable(classes_data, days=5, periods_per_day=7, class_timing=None):
    model = cp_model.CpModel()
    slots = [(d, p) for d in range(days) for p in range(periods_per_day)]

    assign = {}
    for cls, subjects in classes_data.items():
        for si in range(len(subjects)):
            for d, p in slots:
                assign[(cls, si, d, p)] = model.NewBoolVar(f"c_{cls}_{si}_{d}_{p}")

    # Each subject gets exactly its periods per week
    for cls, subjects in classes_data.items():
        for si, subj in enumerate(subjects):
            model.Add(sum(assign[(cls, si, d, p)] for d, p in slots) == subj["periods_per_week"])

    # A subject should not repeat too many times in one day
    for cls, subjects in classes_data.items():
        for si, subj in enumerate(subjects):
            max_per_day = max(1, math.ceil(subj["periods_per_week"] / max(1, days)))
            for d in range(days):
                model.Add(sum(assign[(cls, si, d, p)] for p in range(periods_per_day)) <= max_per_day)

    # A class has only one subject in each period
    for cls, subjects in classes_data.items():
        for d, p in slots:
            model.Add(sum(assign[(cls, si, d, p)] for si in range(len(subjects))) <= 1)

    # Real times of every period, for every class
    use_real_times = bool(class_timing)
    times_by_class = {}
    for cls in classes_data:
        if use_real_times:
            times_by_class[cls] = _period_times(class_timing.get(cls), periods_per_day)
        else:
            times_by_class[cls] = [(p, p + 1) for p in range(periods_per_day)]

    # A teacher cannot teach two lessons that overlap in real time
    teacher_lessons = {}
    for cls, subjects in classes_data.items():
        for si, subj in enumerate(subjects):
            key = _normalize_teacher(subj["teacher"])
            for d in range(days):
                for p in range(periods_per_day):
                    start, end = times_by_class[cls][p]
                    teacher_lessons.setdefault((key, d), []).append((assign[(cls, si, d, p)], start, end))

    for lessons in teacher_lessons.values():
        for t in sorted({start for _, start, _ in lessons}):
            overlapping = [var for var, start, end in lessons if start <= t < end]
            if len(overlapping) > 1:
                model.Add(sum(overlapping) <= 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    result = {cls: {} for cls in classes_data}
    for cls, subjects in classes_data.items():
        for si, subj in enumerate(subjects):
            for d, p in slots:
                if solver.Value(assign[(cls, si, d, p)]):
                    result[cls].setdefault(d, {})[p] = {
                        "subject": subj["subject"],
                        "teacher": subj["teacher"],
                    }
    return result