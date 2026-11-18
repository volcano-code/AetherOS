#!/usr/bin/env bash
set -euo pipefail

EXPECTED_SHA="f7e2898aaefc8f967dbf7345e3999a65672fe60e"
EXPECTED_URL="https://github.com/NousResearch/hermes-agent.git"
EXPECTED_PATH="vendor/hermes"

actual_url="$(git config -f .gitmodules --get "submodule.${EXPECTED_PATH}.url")"
actual_sha="$(git ls-tree HEAD "${EXPECTED_PATH}" | awk '{print $3}')"
actual_mode="$(git ls-tree HEAD "${EXPECTED_PATH}" | awk '{print $1}')"
actual_type="$(git ls-tree HEAD "${EXPECTED_PATH}" | awk '{print $2}')"

[[ "${actual_url}" == "${EXPECTED_URL}" ]] || {
  echo "Unexpected Hermes submodule URL: ${actual_url}" >&2
  exit 1
}
[[ "${actual_sha}" == "${EXPECTED_SHA}" ]] || {
  echo "Unexpected Hermes gitlink SHA: ${actual_sha}" >&2
  exit 1
}
[[ "${actual_mode}" == "160000" && "${actual_type}" == "commit" ]] || {
  echo "vendor/hermes is not a Git submodule gitlink (mode=${actual_mode}, type=${actual_type})" >&2
  exit 1
}

echo "Hermes submodule pin verified: ${actual_sha}"
