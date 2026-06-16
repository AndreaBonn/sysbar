#!/usr/bin/env bash
# Build helper: compile the GSettings schema and translations for local
# development, or install/run the app. The .deb packaging lives under
# packaging/debian and is built in milestone 9.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
SCHEMA_DIR="${BUILD_DIR}/schemas"

compile_schema() {
    mkdir -p "${SCHEMA_DIR}"
    cp "${ROOT_DIR}/data/io.github.AndreaBonn.Sysbar.gschema.xml" "${SCHEMA_DIR}/"
    glib-compile-schemas "${SCHEMA_DIR}"
    echo "Schema compiled into ${SCHEMA_DIR}"
}

compile_translations() {
    local locale_root="${ROOT_DIR}/data/locale"
    [ -d "${locale_root}" ] || return 0
    while IFS= read -r -d '' po; do
        msgfmt "${po}" -o "${po%.po}.mo"
        echo "Compiled ${po%.po}.mo"
    done < <(find "${locale_root}" -name '*.po' -print0)
}

run_app() {
    GSETTINGS_SCHEMA_DIR="${SCHEMA_DIR}" uv run sysbar "$@"
}

case "${1:-build}" in
    build)
        compile_schema
        compile_translations
        echo "Run with: GSETTINGS_SCHEMA_DIR=${SCHEMA_DIR} uv run sysbar"
        ;;
    run)
        shift
        compile_schema >/dev/null
        compile_translations >/dev/null
        run_app "$@"
        ;;
    *)
        echo "Usage: ./build.sh [build|run -- <args>]" >&2
        exit 1
        ;;
esac
