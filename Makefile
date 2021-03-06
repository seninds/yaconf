ROOT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
PYTHON ?= python


all: build


build:


check: build
	[ -L "$(ROOT_DIR)/tests/yaconf" ] || \
		ln -s "$(ROOT_DIR)/yaconf" "$(ROOT_DIR)/tests/yaconf"
	${PYTHON} -m unittest discover -s "$(ROOT_DIR)/tests" -v


clean:
	@rm -f "$(ROOT_DIR)/tests/yaconf"
	@find "$(ROOT_DIR)" -type f -name "*.pyc" -delete
	@find "$(ROOT_DIR)" -type d -name "__pycache__" | xargs rm -rf


.PHONY: all build check clean
