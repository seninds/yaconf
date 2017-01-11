all: build


build:


check: build
	python -m unittest discover -s tests -v


clean:
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf "{}" \;


.PHONY: all build check clean
