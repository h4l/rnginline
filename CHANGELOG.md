# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Supported Python versions are now 3.7 – 3.11 (inclusive)
- Project codebase & tooling refreshed

### Fixed

- Resolved deprecation warnings from:
  - old string escape syntax
  - `pkg_resources` module (we now use `importlib_resources`)
  - `docopt` (we now use `docopt-ng`)

## [0.0.2] — 2015-05-30

### Fixed

- Old data file with non-ascii filename was being included in the 0.0.1 build
  (#2).

## [0.0.1] — 2015-03-29

Initial release

[unreleased]:
  https://github.com/olivierlacan/keep-a-changelog/compare/0.0.2...HEAD
[0.0.2]: https://github.com/h4l/rnginline/compare/0.0.1...0.0.2
[0.0.1]: https://github.com/h4l/rnginline/releases/tag/0.0.1