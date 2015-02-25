# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from os import path
import tempfile

import pkg_resources
import pytest
import six

from relaxnginline.test.test_relaxnginline import (
    test_testcases_testcases, ttt_ids)

from relaxnginline.cmdline import main as rng_main
from relaxnginline.test.mini_validator import main as minival_main


@pytest.fixture(scope="module")
def testcase_dir():
    """
    Extract testcase data to the filesystem for access by command line tools.
    """
    return pkg_resources.resource_filename("relaxnginline.test",
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
            pytest.fail("relaxnginline.cmdline exited with status: {0}"
                        .format(e.code))

    try:
        minival_main(argv=_cmdline_args([inlined_schema, xml_external]))
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
