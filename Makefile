ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))


all: build


build:


check: build
	[ -L "$(ROOT_DIR)/tests/yaconf" ] || \
		ln -s "$(ROOT_DIR)/yaconf" "$(ROOT_DIR)/tests/yaconf"
	python -m unittest discover -s "$(ROOT_DIR)/tests" -v


clean:
	@rm -f "$(ROOT_DIR)/tests/yaconf"
	@find "$(ROOT_DIR)" -type f -name "*.pyc" -delete
	@find "$(ROOT_DIR)" -type d -name "__pycache__" -exec rm -rf "{}" \;


.PHONY: all build check clean
