.PHONY: install dev lint format test coverage clean build check-dist docker

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check src/ tests/ scripts/check_dist.py
	mypy src/scholar_agent/

format:
	ruff format src/ tests/ scripts/check_dist.py
	ruff check --fix src/ tests/ scripts/check_dist.py

test:
	python -m pytest tests/ -v

coverage:
	python -m pytest tests/ --cov=scholar_agent --cov-report=term-missing --cov-report=html

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

build:
	python -m build

check-dist:
	rm -rf dist/
	python -m build
	python scripts/check_dist.py --dist-dir dist

docker:
	docker build -t scholar-agent .
