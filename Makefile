# Common tasks for developing SDEM. SDEM itself needs only Python 3.10+ and its standard library.
# Every target runs SDEM from this checkout (python -m sdem); `make setup` also installs the `sdem` command.
PYTHON ?= python3

.PHONY: help setup test check integrity accept example clean

help:          ## list the targets
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

setup:         ## install the sdem command from this checkout (editable)
	$(PYTHON) -m pip install -e .

test:          ## the whole test suite, as CI runs it (several minutes)
	$(PYTHON) -m unittest discover -s tests

check:         ## every generated document and schema is current
	$(PYTHON) -m sdem model check

integrity:     ## SDEM's verdict on the metamodel integrity design, on the complete Payment example
	$(PYTHON) -m sdem model integrity --workspace examples/0.20/payment-initiation-v4/sdem --check

accept:        ## the rules engine passes its acceptance cases
	$(PYTHON) -m sdem model accept

example:       ## the Payments example, built and explored, in work/ (ignored by Git)
	$(PYTHON) -m sdem new --workspace workspaces/payments --person you --example payment-initiation --explore

clean:         ## remove what the targets above write
	rm -rf work workspaces build *.egg-info
