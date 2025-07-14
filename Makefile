.ONESHELL:

lint:
	echo "To lint this project, make sure that you have installed the core" >&2;
	ruff check .

mypy:
	echo "To lint this project, make sure that you have installed the core" >&2;
	mypy -p flamapy

test:
	python -m pytest -sv
