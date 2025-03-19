# AI Football Betting Advisor Makefile

.PHONY: setup run test test-all shadow clean help docker docker-build docker-run

PYTHON = python
PROJECT_NAME = football-betting-advisor
DOCKER_TAG = $(PROJECT_NAME):latest

help:
	@echo "AI Football Betting Advisor"
	@echo ""
	@echo "Usage:"
	@echo "  make setup        Install all dependencies and set up directories"
	@echo "  make run          Run the betting advisor"
	@echo "  make shadow       Run in shadow mode (testing without real money)"
	@echo "  make test         Run tests"
	@echo "  make test-all     Run all tests with coverage"
	@echo "  make check        Run deployment checklist"
	@echo "  make clean        Clean up temporary files"
	@echo "  make docker       Build and run Docker container"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-run   Run Docker container"

setup:
	@echo "Setting up AI Football Betting Advisor..."
	$(PYTHON) scripts/setup.py
	$(PYTHON) -m pip install -r requirements.txt

run:
	@echo "Starting AI Football Betting Advisor..."
	$(PYTHON) main.py

shadow:
	@echo "Starting AI Football Betting Advisor in shadow mode..."
	$(PYTHON) shadow_mode.py

test:
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/

test-all:
	@echo "Running all tests with coverage..."
	$(PYTHON) -m pytest tests/ --cov=. --cov-report=term --cov-report=html

check:
	@echo "Running deployment checklist..."
	$(PYTHON) tests/deployment_checklist.py

clean:
	@echo "Cleaning up..."
	$(PYTHON) scripts/cleanup.py --dry-run
	@echo "To actually delete files, run: python scripts/cleanup.py"
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +

docker-build:
	@echo "Building Docker image..."
	docker build -t $(DOCKER_TAG) .

docker-run:
	@echo "Running Docker container..."
	docker run -d --name $(PROJECT_NAME) --env-file .env -v $(PWD)/data:/app/data -p 8080:8080 $(DOCKER_TAG)

docker: docker-build docker-run
	@echo "Docker container started!"
	@echo "To check logs: docker logs $(PROJECT_NAME)"
	@echo "To stop: docker stop $(PROJECT_NAME)" 