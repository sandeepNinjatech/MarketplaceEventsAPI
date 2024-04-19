.PHONY: run

# Define variables for commands to keep the Makefile clean
PYTHON=python3
PIP=pip3
VENV_DIR=venv
UVICORN=uvicorn
HOST=0.0.0.0
PORT=8000
RELOAD=--reload

# Target to create a virtual environment and install dependencies
setup:
	@echo "Creating virtual environment..."
	@test -d $(VENV_DIR) || $(PYTHON) -m venv $(VENV_DIR)
	@echo "Activating virtual environment..."
	@. $(VENV_DIR)/bin/activate
	@echo "Installing dependencies..."
	@$(PIP) install -r requirements.txt

# Target to run the application
run: setup
	@echo "Starting the FastAPI application..."
	@. $(VENV_DIR)/bin/activate; $(UVICORN) app.main:app --host $(HOST) --port $(PORT) $(RELOAD)

# Optionally add a clean target to clean up the environment
clean:
	@echo "Cleaning up..."
	@rm -rf $(VENV_DIR)
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete
