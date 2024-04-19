.PHONY: run setup clean

# Define variables for commands to keep the Makefile clean
PYTHON=python
PIP=pip
VENV_DIR=venv
UVICORN=uvicorn
HOST=127.0.0.1
PORT=8000
RELOAD=--reload

# Target to create a virtual environment and install dependencies
setup:
	@echo Creating virtual environment...
	@if not exist "$(VENV_DIR)" ($(PYTHON) -m venv $(VENV_DIR))
	@echo Activating virtual environment...
	@call $(VENV_DIR)\Scripts\activate
	@echo Installing dependencies...
	@$(PIP) install -r requirements.txt

# Target to run the application
run: setup
	@echo Starting the FastAPI application...
	@call $(VENV_DIR)\Scripts\activate && $(UVICORN) main:app --host $(HOST) --port $(PORT) $(RELOAD)

# Optionally add a clean target to clean up the environment
clean:
	@echo Cleaning up...
	@if exist "$(VENV_DIR)" (rmdir /s /q $(VENV_DIR))
	@del /s /q *.pyc
	@for /d %%x in (__pycache__) do @rmdir /s /q %%x
