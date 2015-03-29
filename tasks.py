from __future__ import unicode_literals, print_function

import sys
from os import path
import os
import glob
import itertools
import operator

import pkg_resources
from invoke import ctask as task
import six
from six.moves import shlex_quote, reduce
import wheel.pep425tags


ROOT = path.relpath(path.dirname(__file__))


def _pytest_args():
    # On Python 3 we run doctests in modules. The doctests are PY3 specific due
    # to output formatting differences between PY2 and 3. Also, the doctests
    # are just supplemental examples, not the real tests.
    args = ["--pyargs", "rnginline"]
    if six.PY3:
        return ["--doctest-modules"] + args
    return args


@task
def test(ctx, combine_coverage=False):
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
    """
    Test the doctests in the Sphinx docs. Must be run with Python 3."""
    if not six.PY3:
        msg = """\
error: Tried to run doc's doctests with Python 2. They must be run with
Python 3 due to the doctest module not handling formatting differences
between 2 and 3."""
        raise RuntimeError(msg)

    docs(ctx, builder="doctest", cache_dir=cache_dir, out_dir=out_dir,
         warnings_are_errors=True)
    docs(ctx, builder="html", cache_dir=cache_dir, out_dir=out_dir,
         warnings_are_errors=True)


@task
def docs(ctx, builder="html", cache_dir=None, out_dir=None,
         warnings_are_errors=False):
    """Build sphinx documentation"""
    opts = []
    if cache_dir is not None:
        opts += ["-d", cache_dir]
    if warnings_are_errors is True:
        opts += ["-W"]

    out_dir = path.join(ROOT, "docs/_build/") if out_dir is None else out_dir

    ctx.run(cmd(["sphinx-build", "-b", builder] + opts +
                [path.join(ROOT, "docs/"), out_dir]))


@task
def build_dists(ctx):
    """Build distribution packages"""
    ctx.run("python setup.py sdist", pty=True)
    ctx.run("python setup.py bdist_wheel", pty=True)


@task
def test_dists(ctx):
    """Test the build distributions from ./dist/ in isolation"""
    ctx.run("tox -c tox-dist.ini", pty=True)


@task
def test_dist(ctx, dist_type):
    """Test a built distribution"""
    dist_file = get_distribution(dist_type)

    ctx.run(cmd("pip", "install", "--ignore-installed", dist_file), pty=True)

    ctx.run(cmd(["py.test"] + _pytest_args()), pty=True)


def get_distribution(type):
    type_glob = {
        "sdist": "rnginline-*.tar.gz",
        "wheel": "rnginline-*.whl"
    }.get(type)

    if type_glob is None:
        raise ValueError("Unknown distribution type: {0}".format(type))

    pattern = path.join(ROOT, "dist", type_glob)
    dists = glob.glob(pattern)

    if len(dists) != 1:
        raise ValueError("Expected one find one distribution matching: {0!r} "
                         "but got: {1}".format(pattern, len(dists)))

    return dists[0]


@task
def cache_all_requirement_wheels(ctx):
    ctx.run("tox -c tox-wheelcache.ini", pty=True)


def get_platform_tag():
    return wheel.pep425tags.get_abbr_impl() + wheel.pep425tags.get_impl_ver()


@task
def cache_requirement_wheels(ctx):
    wheelhouse = path.join(ROOT, "wheelhouse")
    all_reqs = path.join(ROOT, "requirements", "all.txt")

    with open(all_reqs) as f:
        reqs = list(pkg_resources.parse_requirements(f.read()))

    print("Checking if wheel cache is populated...")

    absent_reqs = []

    for req in reqs:
        print("checking {0} ... ".format(req), end="")
        sys.stdout.flush()

        is_cached_cmd = cmd(
            "pip", "install", "--download", "/tmp/", "--use-wheel",
            "--no-index", "--find-links", wheelhouse, str(req))
        result = ctx.run(is_cached_cmd, warn=True, hide="both")

        if result.ok:
            print("present")
        else:
            print("ABSENT")
            absent_reqs.append(req)

    if absent_reqs:
        print()
        print("Wheel cache is not complete, populating...")

        # Build wheels for all our dependencies, storing them in the wheelhouse
        # dir
        ctx.run(cmd([
            "pip", "wheel",
            # Make built wheels specific to interpreter running this.
            # Required because non-wheel packages like pytest are not
            # necessarily universal. e.g. pytest for python 2.6 requires
            # argparse, but 2.7, 3.3, 3.4 don't.
            "--build-option", "--python-tag=" + get_platform_tag(),
            "--wheel-dir", wheelhouse] +
            list(map(six.text_type, absent_reqs))))

    print()
    print("Done")


@task
def gen_requirements_all(ctx, write=False):
    files = (path.join(ROOT, "requirements", f)
             for f in os.listdir(path.join(ROOT, "requirements"))
             if f != "all.txt")
    all_requirements = reduce(operator.add, map(load_requirements, files), [])
    unique_requirements = merge_requirements(all_requirements)

    all = "\n".join(six.text_type(req) for req in unique_requirements)

    if write is False:
        print(all)
    else:
        with open(path.join(ROOT, "requirements", "all.txt"), "w") as f:
            f.write("# Auto generated by $ inv gen_requirements_all\n")
            f.write(all)
            f.write("\n")


def load_requirements(file):
    with open(file) as f:
        return list(pkg_resources.parse_requirements(f.read()))


def merge_dupes(reqs):
    merged = set(reqs)
    assert len(merged) != 0
    if len(merged) > 1:
        raise ValueError(
            "Duplicate requirement for {} with differing version/extras: {}"
            .format(next(iter(merged)).key, merged))
    return next(iter(merged))


def merge_requirements(reqs):
    reqs = sorted(reqs, key=lambda r: r.key)
    grouped = itertools.groupby(reqs, key=lambda r: r.key)
    return set(merge_dupes(dupes) for (key, dupes) in grouped)


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
