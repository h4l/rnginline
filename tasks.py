from __future__ import unicode_literals, print_function

from os import path

from invoke import ctask as task
import six
from six.moves import shlex_quote


ROOT = path.relpath(path.dirname(__file__))


def _pytest_args():
    # On Python 3 we run doctests in modules. The doctests are PY3 specific due
    # to output formatting differences between PY2 and 3. Also, the doctests
    # are just supplemental examples, not the real tests.
    args = ["rnginline/"]
    if six.PY3:
        return ["--doctest-modules"] + args
    return args


@task
def test(ctx, combine_coverage=True):
    """Run rnginline test suite"""
    cov_args = ["--parallel-mode"] if combine_coverage is True else []
    ctx.run(cmd(["coverage", "run"] + cov_args +
                ["-m", "pytest"] + _pytest_args()))

    if not combine_coverage:
        _report_coverage(ctx)


def _report_coverage(ctx):
    ctx.run("coverage report")


@task
def coverage(ctx):
    """
    Combine coverage of Python 2 and Python 3 test runs

    This captures Python 2/3 specific code branches in coverage results.
    """
    print("Combining coverage of Python 2 and 3 test runs:")
    print("===============================================")
    ctx.run("coverage erase")

    ctx.run("tox -e py27,py34 -- --combine-coverage")
    ctx.run("coverage combine")
    ctx.run("coverage html")
    print()
    print("Combined coverage of Python 2 and 3 test runs:")
    print("==============================================")
    print()
    _report_coverage(ctx)


@task
def pep8(ctx):
    """Lint code for PEP 8 violations"""
    ctx.run("flake8 --version")
    ctx.run("flake8 setup.py tasks.py rnginline")


@task
def readme(ctx):
    """Lint the README for reStructuredText syntax issues"""
    ctx.run("restructuredtext-lint README.rst")


@task
def docs_test(ctx, cache_dir=None, out_dir=None):
    docs(ctx, builder="doctest", cache_dir=cache_dir, out_dir=out_dir,
         warnings_are_errors=True)
    docs(ctx, builder="html", cache_dir=cache_dir, out_dir=out_dir,
         warnings_are_errors=True)


@task
def docs(ctx, builder="html", cache_dir=None, out_dir="docs/_build/",
         warnings_are_errors=False):
    """Build sphinx documentation"""
    opts = []
    if cache_dir is not None:
        opts += ["-d", cache_dir]
    if warnings_are_errors is True:
        opts += ["-W"]

    out_dir = "docs/_build/" if out_dir is None else out_dir

    ctx.run(cmd(["sphinx-build", "-b", builder] + opts +
                [path.join(ROOT, "docs/"), out_dir]))


def cmd(*args):
    r"""
    Create a shell command string from a list of arguments.

    >>> print(cmd("a", "b", "c"))
    a b c
    >>> print(cmd(["ls", "-l", "some dir"]))
    ls -l 'some dir'
    >>> print(cmd(["echo", "I'm a \"string\"."]))
    echo 'I'"'"'m a "string".'
    """
    if len(args) == 1 and not isinstance(args[0], six.string_types):
        return cmd(*args[0])
    return " ".join(shlex_quote(arg) for arg in args)
