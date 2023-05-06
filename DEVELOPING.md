# Developer Instructions

We have a devcontainer config in the `.devcontainer/` directory. Visual Studio
Code should offer to open the project in a devcontainer automatically.

We use direnv to automatically export environment variables, so install direnv
and run `direnv allow` (after reading `.envrc` to check you trust it).

## Python Version Testing

We test against supported Python versions by using docker compose to run tests
in containers for every version.

Run all unit tests:

```console
$ docker compose --profile unit_test up
```

Run tests for a specific version:

```console
$ docker compose run test_py3.7
```

Run tests for a specific version with a custom command:

```console
$ docker compose run test_py3.7 poetry run pytest --exitfirst --showlocals
```

Test distribution packages:

(This installs the wheel/source dists into Python containers for each version to
check that the packages work.)

```console
$ poetry build
Building rnginline (0.0.2)
  - Building sdist
  - Built rnginline-0.0.2.tar.gz
  - Building wheel
  - Built rnginline-0.0.2-py3-none-any.whl
direnv: loading /workspaces/rnginline/.envrc
direnv: export +COMPOSE_FILE +RNGINLINE_DEVCONTAINER_VOLUME +RNGINLINE_DISTRIBUTION_FILES
$ echo $RNGINLINE_DISTRIBUTION_FILES
dist/rnginline-0.0.2-py3-none-any.whl
dist/rnginline-0.0.2.tar.gz
$ docker compose --profile distribution_test up
...
```
