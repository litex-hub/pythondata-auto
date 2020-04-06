
ACTIVATE=source ./venv/bin/activate;

SHELL := /bin/bash

clean:
	rm -rf venv

.PHONY: clean

venv: requirements.txt
	virtualenv --python python3 venv
	$(ACTIVATE) pip install -r requirements.txt

.PHONY: venv

update:
	$(ACTIVATE) python update.py

.PHONY: update
