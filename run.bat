@echo off
REM Check if the virtual environment folder exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate the virtual environment
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run the FastAPI application
echo Starting the FastAPI application...
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

echo Script completed!
pause
