"""
Employee Attendance & Analytics API - STARTER

Run:  uvicorn app.main:app --port 8000
Env:  MONGO_URI, MONGO_DB (a local .env is loaded for convenience)

This file was written quickly by a colleague who has left the company. The happy path
works, but nobody has reviewed it. Read PROBLEM_STATEMENT.docx for what is expected of you,
openapi.yaml for the contract and DATA_MODEL.md for what is stored in MongoDB.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
from pymongo.errors import DuplicateKeyError
from contextlib import asynccontextmanager
from pymongo import MongoClient, ReturnDocument
load_dotenv()

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGO_DB", "attendance_db")]

IST = timezone(timedelta(hours=5, minutes=30))

app = FastAPI(title="Employee Attendance & Analytics API", version="2.0.0")
def create_indexes():
    db.employees.create_index(
        [("emp_code", 1)],
        unique=True,
        name="uq_employee_code",
    )

    db.attendance_logs.create_index(
        [("emp_code", 1), ("date", 1)],
        unique=True,
        name="uq_attendance_employee_date",
    )

    db.attendance_logs.create_index(
        [("date", -1), ("emp_code", 1)],
        name="ix_attendance_date_employee",
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        client.admin.command("ping")
        create_indexes()
    except Exception:
        import logging
        logging.exception("MongoDB startup check or index creation failed")

    yield


app = FastAPI(
    title="Employee Attendance & Analytics API",
    version="2.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def truncate_to_seconds(value: datetime) -> datetime:
    """Remove fractional seconds from a timestamp."""
    return value.replace(microsecond=0)


def parse_epoch_ms(value: Optional[int]) -> datetime:
    """Validate epoch milliseconds and convert them to an IST datetime."""
    if value is None:
        return truncate_to_seconds(datetime.now(IST))

    # bool is a subclass of int in Python, so reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise HTTPException(422, "Timestamp must be an integer in epoch milliseconds")

    if value < 100_000_000_000:
        raise HTTPException(422, "Timestamp must be in epoch milliseconds")

    try:
        result = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        return truncate_to_seconds(result.astimezone(IST))
    except (OverflowError, OSError, ValueError):
        raise HTTPException(422, "Timestamp is out of range")


def get_shift_start(
    punch_in: datetime,
    shift_start: str,
    shift_end: str,
) -> datetime:
    """Find the start of the shift associated with this punch-in."""
    start_hour, start_minute = map(int, shift_start.split(":"))
    end_hour, end_minute = map(int, shift_end.split(":"))

    shift_start_time = punch_in.replace(
        hour=start_hour, minute=start_minute, second=0, microsecond=0
    )
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute
    punch_minutes = punch_in.hour * 60 + punch_in.minute

    # An overnight shift's early-morning punch belongs to the previous day.
    if end_minutes <= start_minutes and punch_minutes < end_minutes:
        shift_start_time -= timedelta(days=1)

    return shift_start_time


def get_shift_end(
    punch_in: datetime,
    shift_start: str,
    shift_end: str,
) -> datetime:
    """Find the end of the shift associated with this punch-in."""
    start_hour, start_minute = map(int, shift_start.split(":"))
    end_hour, end_minute = map(int, shift_end.split(":"))

    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute

    shift_end_time = punch_in.replace(
        hour=end_hour, minute=end_minute, second=0, microsecond=0
    )

    if end_minutes <= start_minutes:
        if punch_in.hour * 60 + punch_in.minute < end_minutes:
            # Punch-in is after midnight, within the previous day's shift.
            return shift_end_time
        return shift_end_time + timedelta(days=1)

    return shift_end_time


def compute_late_minutes(
    punch_in: datetime,
    shift_start: str,
    shift_end: str,
) -> int:
    shift_start_dt = get_shift_start(punch_in, shift_start, shift_end)
    difference_seconds = (punch_in - shift_start_dt).total_seconds()

    # Must be strictly more than 10 minutes late.
    if difference_seconds <= 10 * 60:
        return 0

    return int(difference_seconds // 60)


def compute_work_hours(punch_in: datetime, punch_out: datetime) -> float:
    seconds = Decimal(
        str((truncate_to_seconds(punch_out) -
             truncate_to_seconds(punch_in)).total_seconds())
    )
    hours = seconds / Decimal("3600")

    return float(
        hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def compute_overtime(
    punch_in: datetime,
    punch_out: datetime,
    shift_start: str,
    shift_end: str,
) -> int:
    shift_end_dt = get_shift_end(punch_in, shift_start, shift_end)
    difference_seconds = (punch_out - shift_end_dt).total_seconds()

    # Overtime counts only when the employee works at least 30 minutes extra.
    if difference_seconds < 30 * 60:
        return 0

    return int(difference_seconds // 60)


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class EmployeeIn(BaseModel):
    emp_code: str
    name: str
    email: str
    department: str
    shift_start: str = "09:30"
    shift_end: str = "18:30"
    joined_on: str



class PunchInIn(BaseModel):
    emp_code: str
    punched_at: Optional[int] = None
    status: Literal["PRESENT", "WFH", "ON_DUTY"] = "PRESENT"



class PunchOutIn(BaseModel):
    emp_code: str
    punched_at: Optional[int] = None



# --------------------------------------------------------------------------- #
# Endpoints provided
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    try:
        client.admin.command("ping")
        return {"status": "ok"}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="MongoDB unavailable",
        )




@app.post("/employees", status_code=201)
def create_employee(body: EmployeeIn):
    doc = body.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)

    try:
        db.employees.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="emp_code already exists",
        )

    return {
        "emp_code": doc["emp_code"],
        "name": doc["name"],
        "email": doc["email"],
        "department": doc["department"],
        "shift_start": doc["shift_start"],
        "shift_end": doc["shift_end"],
        "joined_on": doc["joined_on"],
        "created_at": int(doc["created_at"].timestamp() * 1000),
    }




@app.get("/employees")
def list_employees(
    department: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    if page < 1:
        raise HTTPException(422, "page must be at least 1")

    if page_size < 1 or page_size > 100:
        raise HTTPException(422, "page_size must be between 1 and 100")

    q = {}
    if department:
        q["department"] = department

    total = db.employees.count_documents(q)

    items = list(
        db.employees.find(q, {"_id": 0})
        .sort("emp_code", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    # API timestamps must be epoch milliseconds.
    for item in items:
        created_at = item.get("created_at")
        if isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            item["created_at"] = int(created_at.timestamp() * 1000)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }




@app.post("/attendance/punch-in", status_code=201)
def punch_in(body: PunchInIn):
    emp = db.employees.find_one({"emp_code": body.emp_code})

    if emp is None:
        raise HTTPException(404, "Employee not found")

    ts = parse_epoch_ms(body.punched_at)
    attendance_date = ts.date().isoformat()

    doc = {
        "emp_code": body.emp_code,
        "date": attendance_date,
        "status": body.status,
        "punch_in": ts,
        "punch_out": None,
        "work_hours": None,
        "late_minutes": compute_late_minutes(
            ts,
            emp["shift_start"],
            emp["shift_end"],
        ),
        "overtime_minutes": 0,
        "half_day": False,
        "history": [],
    }

    try:
        db.attendance_logs.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(
            409,
            "Already punched in for this employee and date",
        )

    # Do not expose MongoDB's internal _id.
    return {
        "emp_code": doc["emp_code"],
        "date": doc["date"],
        "status": doc["status"],
        "punch_in": int(ts.timestamp() * 1000),
        "punch_out": None,
        "work_hours": None,
        "late_minutes": doc["late_minutes"],
        "overtime_minutes": 0,
        "half_day": False,
        "history": [],
    }



@app.post("/attendance/punch-out")
def punch_out(body: PunchOutIn):
    # Confirm the employee exists.
    emp = db.employees.find_one({"emp_code": body.emp_code})
    if emp is None:
        raise HTTPException(404, "Employee not found")

    # Convert and validate epoch milliseconds; use IST.
    ts = parse_epoch_ms(body.punched_at)

    # Find the most recent attendance record opened by this time.
    record = db.attendance_logs.find_one(
        {
            "emp_code": body.emp_code,
            "punch_in": {"$ne": None, "$lte": ts},
        },
        sort=[("punch_in", -1)],
    )

    if record is None:
        raise HTTPException(404, "No punch-in found")

    if record.get("punch_out") is not None:
        raise HTTPException(409, "Attendance record already punched out")

    
    punch_in_time = record["punch_in"]

# MongoDB returns naive datetimes in UTC by default.
# Convert the stored timestamp to timezone-aware IST.
    if punch_in_time.tzinfo is None:
       punch_in_time = punch_in_time.replace(
        tzinfo=timezone.utc
    ).astimezone(IST)
    else:
       punch_in_time = punch_in_time.astimezone(IST)

    duration_seconds = (ts - punch_in_time).total_seconds()


    if duration_seconds <= 0:
        raise HTTPException(422, "Punch-out must be after punch-in")

    if duration_seconds > 24 * 60 * 60:
        raise HTTPException(422, "Punch-out must be within 24 hours of punch-in")

    # Normalize instants to whole seconds before calculating derived fields.
    ts = truncate_to_seconds(ts)
    punch_in_time = truncate_to_seconds(punch_in_time)

    work_hours = compute_work_hours(punch_in_time, ts)
    overtime_minutes = compute_overtime(
        punch_in_time,
        ts,
        emp["shift_start"],
        emp["shift_end"],
    )
    half_day = work_hours < 4.50

    # Atomic conditional update: concurrent punch-outs cannot both succeed.
    updated = db.attendance_logs.find_one_and_update(
        {
            "_id": record["_id"],
            "punch_out": None,
        },
        {
            "$set": {
                "punch_out": ts,
                "work_hours": work_hours,
                "overtime_minutes": overtime_minutes,
                "half_day": half_day,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if updated is None:
        raise HTTPException(409, "Attendance record already punched out")

    # Return the API representation, not MongoDB's internal _id.
    return {
        "emp_code": updated["emp_code"],
        "date": updated["date"],
        "status": updated["status"],
        "punch_in": int(punch_in_time.timestamp() * 1000),
        "punch_out": int(ts.timestamp() * 1000),
        "work_hours": updated["work_hours"],
        "late_minutes": updated.get("late_minutes", 0),
        "overtime_minutes": updated["overtime_minutes"],
        "half_day": updated["half_day"],
        "history": updated.get("history", []),
    }


@app.get("/attendance")
def list_attendance(
    emp_code: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    # Validate pagination
    if page < 1:
        raise HTTPException(422, "page must be at least 1")

    if page_size < 1 or page_size > 100:
        raise HTTPException(422, "page_size must be between 1 and 100")

    # Validate dates
    for date_value in (date_from, date_to):
        if date_value is not None:
            try:
                datetime.strptime(date_value, "%Y-%m-%d")
                # Reject non-canonical formats such as 2026-1-2
                if datetime.strptime(date_value, "%Y-%m-%d").date().isoformat() != date_value:
                    raise ValueError
            except ValueError:
                raise HTTPException(422, "Dates must use YYYY-MM-DD format")

    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must not be after date_to")

    # Build the MongoDB filter
    q = {}

    if emp_code:
        q["emp_code"] = emp_code

    if date_from or date_to:
        q["date"] = {}

        if date_from:
            q["date"]["$gte"] = date_from

        if date_to:
            q["date"]["$lte"] = date_to

    if status:
        q["status"] = status

    # Count ALL matching records, not just the current page
    total = db.attendance_logs.count_documents(q)

    # Fetch only the requested page, in contract order
    page_docs = list(
        db.attendance_logs.find(q, {"_id": 0})
        .sort([("date", -1), ("emp_code", 1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    return {
        "items": page_docs,
        "total": total,
        "page": page,
        "page_size": page_size,
    }



# --------------------------------------------------------------------------- #
# TODO - the rest of the contract (see openapi.yaml):
#   POST  /attendance/punch-out
#   PATCH /attendance/{emp_code}/{date}
#   GET   /analytics/employees/{emp_code}/monthly
#   GET   /analytics/departments/summary
#   GET   /analytics/leaderboard/late
#   GET   /analytics/departments/{department}/trend
#   GET   /admin/explain/{endpoint}
# --------------------------------------------------------------------------- #
