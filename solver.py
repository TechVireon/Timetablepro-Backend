from ortools.sat.python import cp_model
import math


def generate_timetable(classes_data, days=5, periods_per_day=7):
    model = cp_model.CpModel()
    slots = [(d, p) for d in range(days) for p in range(periods_per_day)]

    assign = {}
    for cls, subjects in classes_data.items():
        for si, subj in enumerate(subjects):
            for d, p in slots:
                assign[(cls, si, d, p)] = model.NewBoolVar(f"{cls}_{si}_{d}_{p}")

    # Each subject must get exactly its required periods per week
    for cls, subjects in classes_data.items():
        for si, subj in enumerate(subjects):
            model.Add(sum(assign[(cls, si, d, p)] for d, p in slots) == subj["periods_per_week"])
    # A subject should not repeat too many times in a single day
    for cls, subjects in classes_data.items():
        for si, subj in enumerate(subjects):
            max_per_day = max(1, math.ceil(subj["periods_per_week"] / days))
            for d in range(days):
                model.Add(sum(assign[(cls, si, d, p)] for p in range(periods_per_day)) <= max_per_day)        

    # A class can only study one subject per slot
    for cls, subjects in classes_data.items():
        for d, p in slots:
            model.Add(sum(assign[(cls, si, d, p)] for si in range(len(subjects))) <= 1)

    # A teacher can only teach one class per slot
    teachers = {subj["teacher"] for subjects in classes_data.values() for subj in subjects}
    for teacher in teachers:
        for d, p in slots:
            teacher_vars = [
                assign[(cls, si, d, p)]
                for cls, subjects in classes_data.items()
                for si, subj in enumerate(subjects) if subj["teacher"] == teacher
            ]
            if teacher_vars:
                model.Add(sum(teacher_vars) <= 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    result = {cls: {} for cls in classes_data}
    for cls, subjects in classes_data.items():
        for si, subj in enumerate(subjects):
            for d, p in slots:
                if solver.Value(assign[(cls, si, d, p)]):
                    result[cls].setdefault(d, {})[p] = {"subject": subj["subject"], "teacher": subj["teacher"]}
    return result