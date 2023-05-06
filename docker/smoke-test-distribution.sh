#!/usr/bin/env bash

# This script generates the docker-compose*.json configs in this directory.
# To re-generate the configs, run it without any arguments.

set -xeuo pipefail
docker_dir=$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" && pwd)

if (( $# == 0 )); then
    echo "Error: no distributions specified as command line arguments" >&2
    exit 1
fi

for dist in "$@"; do
    if [[ ! -f "$dist" ]]; then
        echo "Error: specified distribution path does not exist on disk: $dist" >&2
        exit 1
    fi
    abs_dist=$(readlink -f "$dist")

    venv_dir=$(mktemp -d)
    python -m venv "${venv_dir:?}"
    $venv_dir/bin/pip install "${abs_dist:?}" || {
        echo "Error: failed to install distribution: $dist" >&2;
        exit 1
    }

    # We just need to smoke test the distribution. i.e. make sure we can run the
    # rnginline command, and it can succesfully inline a schema.
    schema_file=$(mktemp)
    external_ref_example="${docker_dir:?}/../rnginline/test/data/testcases/external-ref-1"
    $venv_dir/bin/rnginline \
        "${external_ref_example:?}/schema.rng" \
        "${schema_file:?}" || {
        echo "Error: rnginline failed to inline the schema" >&2;
        exit 1
    }
    # Make sure the inlined schema works
    $venv_dir/bin/python "${docker_dir:?}/../rnginline/test/mini_validator.py" \
        "${schema_file:?}" "${external_ref_example:?}/positive-1.xml" || {
        echo "Error: the schema rnginline created failed to validate a valid XML doc" >&2;
        exit 1
    }
done
