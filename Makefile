PYTHONPATH=./src/
PYTHON=./venv/bin/python

REPO_NAME=starplot-milkyway

VERSION=$(shell uv run python -c 'from build import __version__; print(__version__)')
VERSION_CHECK=$(shell gh release list \
		-R steveberardi/$(REPO_NAME) \
		--limit 1000 \
		--json tagName \
		--jq '.[] | select(.tagName == "v$(VERSION)")' | wc -c)


DATA_PATH=$(shell pwd)/data/

# Environment Variables ------------------------------------------
export STARPLOT_DATA_PATH=$(DATA_PATH)

# ------------------------------------------------------------------
install:
	[ -d ".venv" ] || uv venv && uv pip install -r requirements.txt

format:
	uv run ruff format build.py $(ARGS)
	uv run ruff check build.py --fix $(ARGS)

clean:
	rm -rf __pycache__
	rm -rf venv
	rm -rf build

build:
	rm -rf build
	rm -f build.log
	@mkdir -p build
	@mkdir -p data
	uv run build.py

build-gaia:
# 	rm -rf build
# 	rm -f build.log
# 	@mkdir -p build
# 	@mkdir -p data
	$(PYTHON) gaia.py

# Releases ------------------------------------------
release-check:
	@CHECK="$(VERSION_CHECK)";  \
	if [ $$CHECK -eq 0 ] ; then \
		echo "version check passed!"; \
	else \
		echo "version tag already exists"; \
		false; \
	fi

release: release-check
	gh release create \
		v$(VERSION) \
		build/milky_way-$(VERSION).parquet \
		build/milkyway-$(VERSION).svg \
		build/overlay-$(VERSION).png \
		--title "v$(VERSION)" \
		-R steveberardi/$(REPO_NAME)

version:
	@echo $(VERSION)


.PHONY: clean test release release-check build
