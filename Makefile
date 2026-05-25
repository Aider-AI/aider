.PHONY: all version v test t install i build b dist d clean c

all: clean test install build version

version v:
	git describe --tags ||:
	python -m setuptools_scm

test t:
	echo todo pytest --cov=src/pylibtypes tests/ --cov-report term-missing

install i:
	pip install --upgrade --force-reinstall -e . \
	&& pip show aider-chat

build b:
	# SETUPTOOLS_SCM_PRETEND_VERSION=0.0.1
	python -m build

dist d: clean test build
	scripts/check-version.sh
	twine upload dist/*

clean c:
	rm -rfv out dist build/bdist.*
