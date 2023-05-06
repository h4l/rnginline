#!/usr/bin/env bash

# This script generates the docker-compose*.json configs in this directory.
# To re-generate the configs, run it without any arguments.

set -euo pipefail
cd -- "$( dirname -- "${BASH_SOURCE[0]}" )"

PYTHON_VERSIONS_JSON='["3.7", "3.8", "3.9", "3.10", "3.11"]'

jq --null-input \
    --slurpfile unit_test_service_template unit-test-service-template.json \
    --slurpfile dist_test_service_template dist-test-service-template.json \
    --argjson python_versions "${PYTHON_VERSIONS_JSON:?}" \
    '[
        $python_versions[] |
        . as $python_version |
        $unit_test_service_template[] |
        .build.args.python_version |= $python_version |
        {key: "test_py\($python_version)", value: .}
    ] + [
        $python_versions[] |
        . as $python_version |
        $dist_test_service_template[] |
        .image |= "python:\($python_version)" |
        {key: "distribution_test_py\($python_version)", value: .}
    ] | from_entries as $services |
    {
        version: "3.9",
        services: $services
    }
    ' > docker-compose.json

jq --null-input --argjson python_versions "${PYTHON_VERSIONS_JSON:?}" '
    {
        version: "3.9",
        services: (
            $python_versions | map(
                [{name: "test_py\(.)", mode: "rw"},
                 # Security: Mount distribution test volumes readonly so that
                 # the testing container is not able to write to the
                 # distribution after the build and prior to publication.
                 {name: "distribution_test_py\(.)", mode: "ro"}][] |
                {
                    key: .name,
                    value: {volumes: ["devcontainer_volume:/workspaces:\(.mode)"]}
                }
            ) | from_entries
        ),
        volumes: {
            devcontainer_volume: {
                name: "${RNGINLINE_DEVCONTAINER_VOLUME:?}",
                external: true
            }
        }
    }' > docker-compose.devcontainer.json

jq --null-input --argjson python_versions "${PYTHON_VERSIONS_JSON:?}" '
    {
        version: "3.9",
        services: (
            $python_versions | map(
                [{name: "test_py\(.)", mode: "rw"},
                 # Security: Mount distribution test volumes readonly so that
                 # the testing container is not able to write to the
                 # distribution after the build and prior to publication.
                 {name: "distribution_test_py\(.)", mode: "ro"}][] |
                {
                    key: .name,
                    value: {volumes: ["..:/workspaces/rnginline:\(.mode)"]}
                }
            ) | from_entries
        ),
    }' > docker-compose.local.json
