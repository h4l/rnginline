from __future__ import annotations

import io
import os
import re
import tempfile
from contextlib import contextmanager
from os import path
from typing import Generator
from unittest.mock import Mock

import pkg_resources
import pytest
from lxml import etree

from rnginline import _get_cwd, urlhandlers
from rnginline.cmdline import main as rng_main
from rnginline.exceptions import RelaxngInlineError
from rnginline.test.mini_validator import main as minival_main
from rnginline.test.test_rnginline import test_testcases_testcases, ttt_ids


def _code(sysexit: SystemExit | int) -> str | int | None:
    # For some py.test's ExceptionInfo objects in Py26 have an int for the
    # .value attr instead of the actual exception.
    if isinstance(sysexit, int):
        return sysexit
    return sysexit.code


@contextmanager
def change_dir(path: str) -> Generator[str, None, None]:
    old_cwd = _get_cwd()
    os.chdir(path)
    yield path
    os.chdir(old_cwd)


def test_change_dir() -> None:
    old_cwd = _get_cwd()
    new_dir = tempfile.mkdtemp()

    with change_dir(new_dir) as dir:
        assert dir == new_dir
        assert path.realpath(_get_cwd()) == path.realpath(new_dir)

    assert path.realpath(_get_cwd()) == path.realpath(old_cwd)
    os.rmdir(new_dir)


@pytest.fixture(scope="module")
def testcase_dir() -> str:
    """
    Extract testcase data to the filesystem for access by command line tools.
    """
    return pkg_resources.resource_filename("rnginline.test", "data/testcases")


def _external_path(testcase_dir: str, pkg_path: str) -> str:
    assert pkg_path.startswith("data/testcases/")
    tc_path = pkg_path[len("data/testcases/") :]
    return path.join(testcase_dir, tc_path)


@pytest.mark.parametrize(
    "schema_file,test_file,should_match", test_testcases_testcases, ids=ttt_ids
)
def test_cmdline(
    testcase_dir: str, schema_file: str, test_file: str, should_match: bool
) -> None:
    schema_external = _external_path(testcase_dir, schema_file)
    xml_external = _external_path(testcase_dir, test_file)

    # Get a temp file to write the inlined schema to
    fd, inlined_schema = tempfile.mkstemp()
    os.fdopen(fd).close()

    # Generate the inlined schema with the command line tool
    try:
        rng_main(argv=[schema_external, inlined_schema])
    except SystemExit as e:
        if e.code not in [None, 0]:
            pytest.fail("rnginline.cmdline exited with status: {0}".format(e.code))

    try:
        minival_main(argv=[inlined_schema, xml_external])
        status: str | int | None = 0
    except SystemExit as e:
        status = 0 if e.code is None else e.code

    # Cleanup the schema we generated
    os.unlink(inlined_schema)

    if status not in [0, 2]:
        pytest.fail("mini_validator exited abnormally: {0}".format(status))

    if should_match:
        if status != 0:
            pytest.fail(
                "{0} should match {1} but didn't".format(test_file, schema_file)
            )
    else:
        if status != 2:
            pytest.fail(
                "{0} shouldn't match {1} but did".format(test_file, schema_file)
            )


def test_cmdline_from_non_ascii_dir(testcase_dir: str) -> None:
    schema = _external_path(testcase_dir, "data/testcases/xml-base/schema.rng")
    xml = _external_path(testcase_dir, "data/testcases/xml-base/positive-1.xml")

    with change_dir(tempfile.mkdtemp(suffix="-åß∂ƒ\U00010438-")) as new_dir:
        inlined_schema = "schema-inlined.rng"

        # Generate the inlined schema with the command line tool
        rng_main(argv=[path.relpath(schema), inlined_schema])

        # Validate the generated schema matches the expected xml
        minival_main(argv=[inlined_schema, path.relpath(xml)])

        os.unlink(inlined_schema)
    os.rmdir(new_dir)


@pytest.mark.parametrize("base_arg", ["--default-base-uri", "--base-uri", "-b"])
@pytest.mark.parametrize(
    "stdout_arg", [[], ["-"]], ids=["implicit stdout", "minus char"]
)
def test_cmdline_stdin_stdout(
    testcase_dir: str,
    stdout_arg: list[str],
    base_arg: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Note that using stdin is rather awkward as it means we don't know what
    # the base URI of the input is. So that has to be set explicitly using
    # --default-base-uri.

    schema_path = "data/testcases/xml-base/schema.rng"

    schema_bytes = urlhandlers.pydata.dereference(
        urlhandlers.pydata.makeurl("rnginline.test", schema_path)
    )
    xml_bytes = urlhandlers.pydata.dereference(
        urlhandlers.pydata.makeurl(
            "rnginline.test", "data/testcases/xml-base/positive-1.xml"
        )
    )

    # The default base URI must be a URI rather than URI-reference
    is_abs = base_arg == "--default-base-uri"
    base = urlhandlers.file.makeurl(
        _external_path(testcase_dir, schema_path), abs=is_abs
    )

    new_stdin = io.BytesIO(schema_bytes)
    new_stdout = io.BytesIO()

    monkeypatch.setattr("sys.stdin", Mock())
    monkeypatch.setattr("sys.stdin.buffer", new_stdin)
    monkeypatch.setattr("sys.stdout", Mock())
    monkeypatch.setattr("sys.stdout.buffer", new_stdout)

    # Generate the inlined schema with the command line tool
    rng_main(argv=[base_arg, base, "--stdin"] + stdout_arg)

    new_stdout.seek(0)
    schema = etree.RelaxNG(file=new_stdout)
    assert schema(etree.XML(xml_bytes))


@pytest.mark.parametrize("base_uri_arg", ["--default-base-uri", "--base-uri", "-b"])
def test_cmdline_rejects_invalid_base_uri(
    base_uri_arg: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad_uri = "/foo bar"  # contains a space

    stderr = io.StringIO()
    monkeypatch.setattr("sys.stderr", stderr)

    with pytest.raises(SystemExit) as excinfo:
        rng_main(argv=[base_uri_arg, bad_uri, "/dev/null"])
    stderr.seek(0)

    assert _code(excinfo.value) == 1
    assert "base-uri" in stderr.read()


def test_cmdline_traceback_produces_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    stderr = io.StringIO()
    monkeypatch.setattr("sys.stderr", stderr)

    # Patch stdin to blow up when read is called
    class MyTestingRngError(RelaxngInlineError):
        pass

    class Boomer(object):
        def read(self) -> None:
            raise MyTestingRngError("boom!")

    stdin = Boomer()
    monkeypatch.setattr("sys.stdin", Mock())
    monkeypatch.setattr("sys.stdin.buffer", stdin)

    with pytest.raises(SystemExit):
        rng_main(argv=["--traceback", "--stdin"])
    stderr.seek(0)

    assert re.search(r"MyTestingRngError\(.boom!.\)", stderr.read())


@pytest.mark.parametrize(
    "compat_arg,should_match_input",
    [
        # If libxml2 compat is disabled then the output will match the input
        (["--no-libxml2-compat"], True),
        # If compat's on (the default) then the input will be modified to put
        # datatypeLibrary on the data el.
        ([], False),
    ],
)
def test_cmdline_no_libxml2_compat_disables_compat(
    compat_arg: list[str], should_match_input: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_xml = (
        '<element name="start" xmlns="http://relaxng.org/ns/structure/1.0" '
        'datatypeLibrary="foo">'
        '<data type="bar"/>'
        "</element>"
    )
    input = etree.tostring(etree.XML(input_xml), method="c14n")

    stdin = io.BytesIO(input)
    stdout = io.BytesIO()

    monkeypatch.setattr("sys.stdin", Mock())
    monkeypatch.setattr("sys.stdin.buffer", stdin)
    monkeypatch.setattr("sys.stdout", Mock())
    monkeypatch.setattr("sys.stdout.buffer", stdout)

    rng_main(argv=compat_arg + ["--stdin"])
    stdout.seek(0)
    output = etree.tostring(etree.XML(stdout.read()), method="c14n")

    assert (input == output) == should_match_input
