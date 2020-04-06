ACTIVATE=[[ -e venv/bin/activate ]] && source venv/bin/activate;

SHELL := /bin/bash

clean:
	@true

.PHONY: clean

venv-clean:
	rm -rf venv

.PHONY: venv-clean

venv: requirements.txt
	virtualenv --python=python3 venv
	${ACTIVATE} pip install -r requirements.txt

.PHONY: venv

update:
	${ACTIVATE} python update.py

.PHONY: update
