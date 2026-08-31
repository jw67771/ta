init:
	pip install -r requirements.txt

isort:
	isort --check-only --recursive ta test

format: isort
	black --target-version py36 ta test

isort-fix:
	isort --recursive ta test

lint: isort
	prospector --no-autodetect test/
	prospector --no-autodetect ta/

test: lint
	coverage run -m unittest discover
	coverage report -m

.PHONY: research research-validate research-index

research-validate:
	python3 research/tools/validate.py

research-index:
	python3 research/tools/build_index.py

research: research-validate research-index
