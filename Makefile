ACTIVATE=[[ -e venv/bin/activate ]] && source venv/bin/activate;

SHELL := /bin/bash

clean:
	rm -rf repos
	rm -rf srcs
	git checkout repos/.keepme
	git checkout srcs/.keepme

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

echo:
	@echo "${ACTIVATE} python update.py"

push:
	${ACTIVATE} python update.py --push

.PHONY: update
