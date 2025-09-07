.PHONY: fmt lint all

fmt:
	isort $$(find . -name '*.py')
	black .

lint:
	flake8 .
	mypy

all: fmt lint
