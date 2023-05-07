# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [1.0.0]

### Changed

- Supported Python versions are now 3.7 – 3.11 (inclusive)
- Project codebase & tooling refreshed

### Fixed

- Handle indirectly-included components when overriding
  ([#5](https://github.com/h4l/rnginline/issues/5))

  Previously when inlining `<include>` elements, the include's override
  components were only able to override components that directly occurred in the
  included schema. If the included schema itself didn't directly contain an
  overridden `<define>` or `<start>` element, but instead included another
  schema that did contain an overridden element, `rnginline` would fail to find
  the indirectly-included element(s) and would fail with an error. (Because
  overrides must match elements in the included schema.)

  Thanks to [takesson](https://github.com/takesson) for reporting this and
  providing a test case to demonstrate the issue.

- Resolved deprecation warnings from:
  - old string escape syntax
  - `pkg_resources` module (we now use `importlib_resources`)
  - `docopt` (we now use `docopt-ng`)

## [0.0.2] — 2015-05-30

### Fixed

- Old data file with non-ascii filename was being included in the 0.0.1 build
  ([#2](https://github.com/h4l/rnginline/issues/2)).

## [0.0.1] — 2015-03-29

Initial release

[unreleased]:
  https://github.com/olivierlacan/keep-a-changelog/compare/1.0.0...HEAD
[1.0.0]: https://github.com/h4l/rnginline/compare/0.0.2...1.0.0
[0.0.2]: https://github.com/h4l/rnginline/compare/0.0.1...0.0.2
[0.0.1]: https://github.com/h4l/rnginline/releases/tag/0.0.1
