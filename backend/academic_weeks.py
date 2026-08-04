from datetime import date, timedelta
from backend.models import AcademicPeriod, SubjectSyllabus

def academic_week_number(target_date: date, period: AcademicPeriod) -> int | None:
    """
    Returns 1-based week number for the target date within the academic period.
    Returns None if target_date is before start_date or after effective_end_date.
    """
    start = date.fromisoformat(period.start_date)
    end = period.effective_end_date
    
    if target_date < start or target_date > end:
        return None
        
    delta = target_date - start
    return (delta.days // 7) + 1

def academic_week_range(week_number: int, period: AcademicPeriod) -> tuple[date, date] | None:
    """
    Returns Monday and Sunday for the given week number.
    Returns None if week_number is less than 1.
    """
    if week_number < 1:
        return None
    start = date.fromisoformat(period.start_date) + timedelta(weeks=week_number - 1)
    end = start + timedelta(days=6)
    return (start, end)

def subjects_for_academic_week(subjects: list[SubjectSyllabus], week_number: int) -> list[dict]:
    """
    Returns a list of dictionaries with subject name, unit names and contents
    matching the week number.
    """
    result = []
    for subject in subjects:
        matched_units = []
        for unit in subject.units:
            if week_number in unit.weeks:
                matched_units.append({
                    "name": unit.name,
                    "contents": unit.contents
                })
        
        if matched_units:
            result.append({
                "subject_name": subject.name,
                "units": matched_units
            })
            
    return result

def events_for_date_range(events: list[dict], start_date: date, end_date: date) -> list[dict]:
    """
    Filters academic events overlapping the range [start_date, end_date].
    An event overlaps if its start <= end_date and its end >= start_date.
    If an event has no start_date, assume start=end=due_date.
    """
    result = []
    for event in events:
        due = event.get("due_date", "")
        if not due:
            continue
            
        try:
            from datetime import datetime
            end_dt = datetime.fromisoformat(due).date()
        except ValueError:
            continue
            
        start = event.get("start_date", "")
        if start:
            try:
                start_dt = datetime.fromisoformat(start).date()
            except ValueError:
                start_dt = end_dt
        else:
            start_dt = end_dt
            
        if start_dt <= end_date and end_dt >= start_date:
            result.append(event)
            
    return result
