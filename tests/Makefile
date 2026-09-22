# CyberScope command shortcuts.

PROJECT_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PYTHON ?= python3
ITERATIONS ?= 100
RUN = cd "$(PROJECT_ROOT)" && $(PYTHON) main.py

.PHONY: help networktest softwaretest usbtest configurationtest securitytest unittest test stabilitytest

help:
	@echo "CyberScope targets:"
	@echo "  make networktest        Run simulated network security tests"
	@echo "  make softwaretest       Run simulated software security tests"
	@echo "  make usbtest            Run simulated USB security tests"
	@echo "  make configurationtest  Run simulated configuration security tests"
	@echo "  make securitytest       Run all simulated security scenarios"
	@echo "  make unittest           Run the Python unit-test suite"
	@echo "  make test               Run unit tests and all simulated scenarios"
	@echo "  make stabilitytest      Run stability testing (ITERATIONS=100 by default)"

networktest:
	$(RUN) test network --simulation

softwaretest:
	$(RUN) test software --simulation

usbtest:
	$(RUN) test usb --simulation

configurationtest:
	$(RUN) test configuration --simulation

securitytest:
	$(RUN) test all --simulation

unittest:
	cd "$(PROJECT_ROOT)" && $(PYTHON) -m unittest discover -s unit_tests -v

test: unittest securitytest

stabilitytest:
	$(RUN) test stability --iterations "$(ITERATIONS)"
