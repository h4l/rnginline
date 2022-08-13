SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.RECIPEPREFIX = >
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# This should be the first rule so that it runs by default when running `$ make`
# without arguments.
help:
> @echo "Targets:"
> grep -P '^([\w-]+)(?=:)' --only-matching Makefile | sort
.PHONY: default

clean:
> rm -rf dist out
.PHONY: clean

install:
> poetry install
.PHONY: install

test:
> pytest --cov
.PHONY: test

out/:
> mkdir out

test-docs: out/
> sphinx-build -W -b doctest docs out/docs
.PHONY: test-docs

typecheck:
> @if dmypy status > /dev/null; then
>  dmypy run rnginline
> else
>   mypy rnginline
> fi
.PHONY: typecheck

lint: check-code-issues check-code-import-order check-code-format
.PHONY: lint

check-code-issues:
> ruff check rnginline
.PHONY: check-code-issues

check-code-import-order:
> isort --check --diff rnginline
.PHONY: check-code-import-order

check-code-format:
> black --check rnginline
.PHONY: check-code-format

reformat-code:
> @if [[ "$$(git status --porcelain)" != "" ]]; then
>   echo "Refusing to reformat code: files have uncommitted changes" >&2 ; exit 1
> fi
> isort rnginline
> black rnginline
.PHONY: reformat-code

docs: out/
> sphinx-build -W -b html docs out/docs
.PHONY: docs
