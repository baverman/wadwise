.PHONY: fmt lint all watch

fmt:
	ruff check --select I --fix
	ruff format

lint:
	ruff check
	mypy

all: fmt lint

watch:
	on-change -e wadwise/web/static -e wadwise/web/src wadwise -- daemon python main.py -b 0.0.0.0
