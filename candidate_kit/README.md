# Employee Attendance & Analytics API

A REST API built using FastAPI and MongoDB to manage employee information and attendance records.

## Requirements

- Python
- MongoDB 6.0 or newer
- Dependencies listed in `requirements.txt`

## Local Setup

Create and activate a virtual environment.

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Configure the following environment variables in a local `.env` file:

- `MONGO_URI` — MongoDB connection URI
- `MONGO_DB` — MongoDB database name

Do not commit `.env` or any secrets to GitHub.

## Run the Application

From the project root, run:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

The API documentation is available at:

`http://127.0.0.1:8000/docs`

The health endpoint is available at:

`http://127.0.0.1:8000/health`

## Implemented Features

- MongoDB health check
- Employee creation and listing
- Attendance punch-in and punch-out
- Basic attendance listing
- Database indexes
- Core attendance calculations

## Current Status

This is a partial implementation of the assignment. Attendance regularization, analytics endpoints, and explain-plan endpoints remain incomplete. Timestamp serialization and further validation and testing are also pending.

## Submission

The repository should contain:

- `app/main.py`
- `requirements.txt`
- `REVIEW.md`
- `DECISIONS.md`
- `README.md`

Do not include `.env` files, secrets, or a Dockerfile.