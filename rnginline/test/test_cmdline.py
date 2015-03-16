# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import os
from os import path
import tempfile
from contextlib import contextmanager

from lxml import etree
import pkg_resources
import pytest
import six

from rnginline import _get_cwd
from rnginline.cmdline import main as rng_main
from rnginline.test.mini_validator import main as minival_main
from rnginline.exceptions import RelaxngInlineError
from rnginline import urlhandlers

from rnginline.test.test_rnginline import (
    test_testcases_testcases, ttt_ids)


def _code(sysexit):
    # For some py.test's ExceptionInfo objects in Py26 have an int for the
    # .value attr instead of the actual exception.
    if isinstance(sysexit, int):
        return sysexit
    return sysexit.code


@contextmanager
def change_dir(path):
    old_cwd = _get_cwd()
    os.chdir(path)
    yield path
    os.chdir(old_cwd)


def test_change_dir():
    old_cwd = _get_cwd()
    new_dir = tempfile.mkdtemp()

    with change_dir(new_dir) as dir:
        assert dir == new_dir
        assert path.realpath(_get_cwd()) == path.realpath(new_dir)

    assert path.realpath(_get_cwd()) == path.realpath(old_cwd)
    os.rmdir(new_dir)


@pytest.fixture(scope="module")
def testcase_dir():
    """
    Extract testcase data to the filesystem for access by command line tools.
    """
    return pkg_resources.resource_filename("rnginline.test",
                                           "data/testcases")


def _external_path(testcase_dir, pkg_path):
    assert pkg_path.startswith("data/testcases/")
    tc_path = pkg_path[len("data/testcases/"):]
    return path.join(testcase_dir, tc_path)


def _cmdline_args(argv):
    if six.PY2:
        return [a.encode("utf-8") for a in argv]
    return argv


@pytest.mark.parametrize("schema_file,test_file,should_match",
                         test_testcases_testcases, ids=ttt_ids)
def test_cmdline(testcase_dir, schema_file, test_file, should_match):
    schema_external = _external_path(testcase_dir, schema_file)
    xml_external = _external_path(testcase_dir, test_file)

    # Get a temp file to write the inlined schema to
    fd, inlined_schema = tempfile.mkstemp()
    os.fdopen(fd).close()

    # Generate the inlined schema with the command line tool
    try:
        rng_main(argv=_cmdline_args([schema_external, inlined_schema]))
    except SystemExit as e:
        if e.code not in [None, 0]:
            pytest.fail("rnginline.cmdline exited with status: {0}"
                        .format(e.code))

    try:
        minival_main(argv=_cmdline_args([inlined_schema, xml_external]))
        status = 0
    except SystemExit as e:
        status = 0 if e.code is None else e.code

    # Cleanup the schema we generated
    os.unlink(inlined_schema)

    if status not in [0, 2]:
        pytest.fail("mini_validator exited abnormally: {0}".format(status))

    if should_match:
        if status != 0:
            pytest.fail("{0} should match {1} but didn't"
                        .format(test_file, schema_file))
    else:
        if status != 2:
            pytest.fail("{0} shouldn't match {1} but did"
                        .format(test_file, schema_file))


def test_cmdline_from_non_ascii_dir(testcase_dir):
    schema = _external_path(testcase_dir, "data/testcases/xml-base/schema.rng")
    xml = _external_path(testcase_dir,
                         "data/testcases/xml-base/positive-1.xml")

    with change_dir(tempfile.mkdtemp(suffix="-åß∂ƒ\U00010438-")) as new_dir:
        inlined_schema = "schema-inlined.rng"

        # Generate the inlined schema with the command line tool
        rng_main(argv=_cmdline_args([path.relpath(schema), inlined_schema]))

        # Validate the generated schema matches the expected xml
        minival_main(argv=_cmdline_args([inlined_schema, path.relpath(xml)]))

        os.unlink(inlined_schema)
    os.rmdir(new_dir)


@pytest.mark.parametrize("base_arg",
                         ["--default-base-uri", "--base-uri", "-b"])
@pytest.mark.parametrize("stdout_arg", [[], ["-"]],
                         ids=["implicit stdout", "minus char"])
def test_cmdline_stdin_stdout(testcase_dir, stdout_arg, base_arg, monkeypatch):
    # Note that using stdin is rather awkward as it means we don't know what
    # the base URI of the input is. So that has to be set explicitly using
    # --default-base-uri.

    schema_path = "data/testcases/xml-base/schema.rng"

    schema_bytes = urlhandlers.pydata.dereference(
        urlhandlers.pydata.makeurl("rnginline.test", schema_path))
    xml_bytes = urlhandlers.pydata.dereference(
        urlhandlers.pydata.makeurl("rnginline.test",
                                   "data/testcases/xml-base/positive-1.xml"))

    # The default base URI must be a URI rather than URI-reference
    is_abs = base_arg == "--default-base-uri"
    base = urlhandlers.file.makeurl(_external_path(testcase_dir, schema_path),
                                    abs=is_abs)

    new_stdin = six.BytesIO(schema_bytes)
    new_stdout = six.BytesIO()
    new_stdin.buffer = new_stdin  # fake sys.stdin.buffer for Py 3
    new_stdout.buffer = new_stdout

    monkeypatch.setattr("sys.stdin", new_stdin)
    monkeypatch.setattr("sys.stdout", new_stdout)

    # Generate the inlined schema with the command line tool
    rng_main(argv=_cmdline_args(
        [base_arg, base, "--stdin"] + stdout_arg))

    new_stdout.seek(0)
    schema = etree.RelaxNG(file=new_stdout)
    assert schema(etree.XML(xml_bytes))


@pytest.mark.parametrize("base_uri_arg",
                         ["--default-base-uri", "--base-uri", "-b"])
def test_cmdline_rejects_invalid_base_uri(base_uri_arg, monkeypatch):
    bad_uri = "/foo bar"  # contains a space

    stderr = six.StringIO()
    monkeypatch.setattr("sys.stderr", stderr)

    with pytest.raises(SystemExit) as excinfo:
        rng_main(argv=_cmdline_args([base_uri_arg, bad_uri, "/dev/null"]))
    stderr.seek(0)

    assert _code(excinfo.value) == 1
    assert "base-uri" in stderr.read()


def test_cmdline_traceback_produces_traceback(monkeypatch):
    stderr = six.StringIO()
    monkeypatch.setattr("sys.stderr", stderr)

    # Patch stdin to blow up when read is called
    class MyTestingRngError(RelaxngInlineError):
        pass

    class Boomer(object):
        def read(self):
            raise MyTestingRngError("boom!")
    stdin = Boomer()
    stdin.buffer = stdin  # emulate sys.stdin.buffer for Py 3
    monkeypatch.setattr("sys.stdin", stdin)

    with pytest.raises(SystemExit):
        rng_main(argv=_cmdline_args(["--traceback", "--stdin"]))
    stderr.seek(0)

    assert re.search("""MyTestingRngError\(.boom!.\)""", stderr.read())


@pytest.mark.parametrize("compat_arg,should_match_input", [
    # If libxml2 compat is disabled then the output will match the input
    (["--no-libxml2-compat"], True),
    # If compat's on (the default) then the input will be modified to put
    # datatypeLibrary on the data el.
    ([], False)
])
def test_cmdline_no_libxml2_compat_disables_compat(
        compat_arg, should_match_input, monkeypatch):
    input = (
        '<element name="start" xmlns="http://relaxng.org/ns/structure/1.0" '
        'datatypeLibrary="foo">'
        '<data type="bar"/>'
        '</element>'
    )
    input = etree.tostring(etree.XML(input), method="c14n")

    stdin = six.BytesIO(input)
    stdout = six.BytesIO()
    stdin.buffer = stdin
    stdout.buffer = stdout

    monkeypatch.setattr("sys.stdin", stdin)
    monkeypatch.setattr("sys.stdout", stdout)

    rng_main(argv=_cmdline_args(compat_arg + ["--stdin"]))
    stdout.seek(0)
    output = etree.tostring(etree.XML(stdout.read()), method="c14n")

    assert (input == output) == should_match_input
