from __future__ import print_function

import io

from setuptools import setup


def get_version(filename):
    """
    Parse the value of the __version__ var from a Python source file
    without running/importing the file.
    """
    import re
    version_pattern = r"^ *__version__ *= *['\"](\d+\.\d+\.\d+)['\"] *$"
    match = re.search(version_pattern, file_contents(filename), re.MULTILINE)

    assert match, ("No version found in file: {0!r} matching pattern: {1!r}"
                   .format(filename, version_pattern))

    return match.group(1)


def file_contents(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def file_lines(path):
    return [line for line in file_contents(path).split("\n")
            if line.strip()]


setup(
    name="rnginline",
    url="https://github.com/h4l/rnginline",
    description="Flatten multi-file RELAX NG schemas",
    long_description=file_contents("README.rst"),
    version=get_version("rnginline/__init__.py"),
    author="Hal Blackburn",
    author_email="hwtb2@cam.ac.uk",
    packages=["rnginline", "rnginline.test"],
    install_requires=file_lines("requirements/install.txt"),
    extras_require={
        "tests": file_lines("requirements/test.txt")
    },
    entry_points={
        "console_scripts": [
            "rnginline = rnginline.cmdline:main"
        ]
    },
    include_package_data=True,
    license='Apache 2.0',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup :: XML",
    ],
    keywords="relaxng relax ng inline schema flatten lxml xml"
)
