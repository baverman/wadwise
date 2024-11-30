.PHONY: fmt lint all

fmt:
	isort .
	black .

lint:
	flake8 .
	mypy

all: fmt lint
