"""
HTTP layer for the student records database.

Exposes the same create, read, update and delete operations as the
command-line tool over a REST API, and serves the console from
``frontend/``.

Run with::

    uvicorn api:app --reload

Connection settings are read from the environment, falling back to the
same local defaults the command-line tool uses::

    MYSQL_HOST      default "localhost"
    MYSQL_PORT      default 3306
    MYSQL_USER      default "root"
    MYSQL_PASSWORD  default ""
    MYSQL_DATABASE  default "crud"
"""

import os
from contextlib import contextmanager
from pathlib import Path

import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent

FRONTEND_DIR = BASE_DIR / "frontend"

TABLE_NAME = "student_details"


DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "crud"),
}


# ============================================================
# Database
# ============================================================

@contextmanager
def get_cursor(commit: bool = False):
    """
    Open a connection, hand back a dictionary cursor, and always close both.
    """

    try:
        connection = mysql.connector.connect(**DB_CONFIG)

    except mysql.connector.Error as error:
        raise HTTPException(
            status_code=503,
            detail=f"Could not reach the database: {error}",
        ) from error

    cursor = connection.cursor(dictionary=True)

    try:
        yield cursor

        if commit:
            connection.commit()

    except mysql.connector.Error as error:
        connection.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    finally:
        cursor.close()
        connection.close()


def create_table() -> None:
    """
    Create the student table when it is not there yet.
    """

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                RollNo INT,
                FullName VARCHAR(30),
                Marks INT
            )
            """
        )


# ============================================================
# Schemas
# ============================================================

class StudentIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=30)
    roll_no: int = Field(ge=0)
    marks: int = Field(ge=0, le=100)


class Student(StudentIn):
    id: int


class Message(BaseModel):
    message: str


class Stats(BaseModel):
    total: int
    average_marks: float
    highest_marks: int
    lowest_marks: int


# ============================================================
# Application
# ============================================================

app = FastAPI(
    title="Student Records API",
    version="1.0.0",
    description=(
        "Create, read, update and delete student records in MySQL. "
        "The records console is served at /ui."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """
    Make sure the table exists before serving traffic.
    """

    try:
        create_table()

    except HTTPException:
        # The console reports the connection state, so startup stays quiet.
        pass


# ============================================================
# Routes
# ============================================================

@app.get("/api/health", tags=["Health"])
def health() -> dict[str, object]:
    """
    Liveness probe that also confirms the database is reachable.
    """

    with get_cursor() as cursor:
        cursor.execute("SELECT 1 AS ok")
        cursor.fetchone()

    return {
        "status": "healthy",
        "database": DB_CONFIG["database"],
        "table": TABLE_NAME,
    }


@app.get("/api/students", response_model=list[Student], tags=["Students"])
def list_students() -> list[Student]:
    """
    Every student record, newest first.
    """

    with get_cursor() as cursor:
        cursor.execute(
            f"SELECT id, RollNo, FullName, Marks FROM {TABLE_NAME} ORDER BY id DESC"
        )
        rows = cursor.fetchall()

    return [_to_student(row) for row in rows]


@app.get("/api/students/stats", response_model=Stats, tags=["Students"])
def student_stats() -> Stats:
    """
    Headline numbers across the whole table.
    """

    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                AVG(Marks) AS average_marks,
                MAX(Marks) AS highest_marks,
                MIN(Marks) AS lowest_marks
            FROM {TABLE_NAME}
            """
        )
        row = cursor.fetchone() or {}

    return Stats(
        total=int(row.get("total") or 0),
        average_marks=round(float(row.get("average_marks") or 0), 1),
        highest_marks=int(row.get("highest_marks") or 0),
        lowest_marks=int(row.get("lowest_marks") or 0),
    )


@app.get("/api/students/{student_id}", response_model=Student, tags=["Students"])
def get_student(student_id: int) -> Student:
    """
    One student record by id.
    """

    with get_cursor() as cursor:
        cursor.execute(
            f"SELECT id, RollNo, FullName, Marks FROM {TABLE_NAME} WHERE id = %s",
            (student_id,),
        )
        row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Student not found.")

    return _to_student(row)


@app.post("/api/students", response_model=Student, status_code=201, tags=["Students"])
def create_student(student: StudentIn) -> Student:
    """
    Add a student record.
    """

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            f"INSERT INTO {TABLE_NAME} (FullName, RollNo, Marks) VALUES (%s, %s, %s)",
            (student.full_name, student.roll_no, student.marks),
        )
        new_id = cursor.lastrowid

    return Student(id=new_id, **student.model_dump())


@app.put("/api/students/{student_id}", response_model=Student, tags=["Students"])
def update_student(student_id: int, student: StudentIn) -> Student:
    """
    Replace a student record.
    """

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            f"UPDATE {TABLE_NAME} SET FullName = %s, RollNo = %s, Marks = %s WHERE id = %s",
            (student.full_name, student.roll_no, student.marks, student_id),
        )

        if cursor.rowcount == 0:
            cursor.execute(
                f"SELECT id FROM {TABLE_NAME} WHERE id = %s",
                (student_id,),
            )

            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Student not found.")

    return Student(id=student_id, **student.model_dump())


@app.delete("/api/students/{student_id}", response_model=Message, tags=["Students"])
def delete_student(student_id: int) -> Message:
    """
    Remove one student record.
    """

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            f"DELETE FROM {TABLE_NAME} WHERE id = %s",
            (student_id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Student not found.")

    return Message(message="Record deleted successfully.")


@app.delete("/api/students", response_model=Message, tags=["Students"])
def delete_all_students() -> Message:
    """
    Empty the table.
    """

    with get_cursor(commit=True) as cursor:
        cursor.execute(f"DELETE FROM {TABLE_NAME}")
        removed = cursor.rowcount

    return Message(message=f"Deleted {removed} record(s).")


# ============================================================
# Helpers
# ============================================================

def _to_student(row: dict) -> Student:
    """
    Map a database row onto the response model.
    """

    return Student(
        id=row["id"],
        full_name=row.get("FullName") or "",
        roll_no=row.get("RollNo") or 0,
        marks=row.get("Marks") or 0,
    )


# ============================================================
# Console
# ============================================================

if FRONTEND_DIR.is_dir():

    app.mount(
        "/ui",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="ui",
    )

    @app.get("/", include_in_schema=False)
    def console() -> RedirectResponse:
        """
        Send the application root to the records console.
        """

        return RedirectResponse(url="/ui/")


__all__ = ["app"]
