# Student Records

A student records database with two front doors: a menu-driven command-line tool and a REST API with a web console. Both work against the same MySQL table.

The CLI is the original program — a compact walkthrough of create, read, update and delete against MySQL from Python. The API wraps the same operations in FastAPI with parameterised queries, and serves a console with live grade statistics.

---

## Highlights

| | |
|---|---|
| **Two interfaces** | A terminal menu and a REST API with a web console |
| **Full CRUD** | Create, read, update and delete, one record or the whole table |
| **Parameterised queries** | The API binds every value rather than building SQL strings |
| **Automatic schema** | The table is created on first start if it is not there |
| **Grade insights** | Distribution histogram, leaderboard and banded counts |
| **Environment driven** | Connection settings come from the environment with local defaults |

---

## The console

Start the API and open the root URL.

**Records** — headline stats (count, average, highest, how many are at or above pass), a live filter, and a grade-band segmented filter. Each row shows a marks bar coloured by band, with inline edit and delete.

**Insights** — a distribution histogram in ten-mark bands, a top-of-the-class leaderboard, and counts for each grade band.

---

## The data

| Column | Type | Meaning |
|---|---|---|
| `id` | `INT AUTO_INCREMENT` | Primary key |
| `RollNo` | `INT` | Roll number |
| `FullName` | `VARCHAR(30)` | Student name |
| `Marks` | `INT` | Marks out of 100 |

Grade bands used by the console:

| Band | Range |
|---|---|
| Distinction | 80 – 100 |
| First class | 60 – 79 |
| Pass | 40 – 59 |
| Below pass | 0 – 39 |

---

## Getting started

### Prerequisites

- Python 3.9 or newer
- MySQL 8

### 1. Install

```bash
git clone https://github.com/harshlaxkar07/crud_mysql.git
cd crud_mysql
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create the database

```sql
CREATE DATABASE IF NOT EXISTS crud;
```

The `student_details` table is created for you when the API starts.

### 3. Configure

The API reads its connection settings from the environment, falling back to the same local defaults the CLI uses:

| Variable | Default |
|---|---|
| `MYSQL_HOST` | `localhost` |
| `MYSQL_PORT` | `3306` |
| `MYSQL_USER` | `root` |
| `MYSQL_PASSWORD` | *(empty)* |
| `MYSQL_DATABASE` | `crud` |

```bash
export MYSQL_USER=root
export MYSQL_PASSWORD=your-password
```

### 4. Run

**Web console and API**

```bash
uvicorn api:app --reload
```

| URL | What it is |
|---|---|
| `http://localhost:8000/` | The records console |
| `http://localhost:8000/docs` | Interactive OpenAPI documentation |
| `http://localhost:8000/api/health` | Health probe confirming the database is reachable |

**Command-line tool**

```bash
python crud_mysql.py
```

```
Select option:
1. create
2. read
3. update
4. delete
5. exit
Input :
```

---

## API reference

| Method | Path | What it does |
|---|---|---|
| `GET` | `/api/health` | Confirms the database is reachable |
| `GET` | `/api/students` | Every record, newest first |
| `GET` | `/api/students/stats` | Count, average, highest and lowest marks |
| `GET` | `/api/students/{id}` | One record |
| `POST` | `/api/students` | Add a record |
| `PUT` | `/api/students/{id}` | Replace a record |
| `DELETE` | `/api/students/{id}` | Remove one record |
| `DELETE` | `/api/students` | Empty the table |

### Adding a student

```bash
curl -X POST http://localhost:8000/api/students \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Aarav Sharma", "roll_no": 101, "marks": 88}'
```

```json
{ "id": 1, "full_name": "Aarav Sharma", "roll_no": 101, "marks": 88 }
```

### Reading the stats

```bash
curl http://localhost:8000/api/students/stats
```

```json
{ "total": 12, "average_marks": 65.2, "highest_marks": 95, "lowest_marks": 29 }
```

---

## Validation

| Field | Rule |
|---|---|
| `full_name` | 1 to 30 characters |
| `roll_no` | Zero or greater |
| `marks` | 0 to 100 |

---

## Project structure

```
crud_mysql/
├── crud_mysql.py      The menu-driven command-line tool
├── api.py             FastAPI application, CRUD routes and the static mount
├── requirements.txt
└── frontend/          The records console
```
