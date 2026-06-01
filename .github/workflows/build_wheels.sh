#!/usr/bin/env bash
#
# Build the bundle of flamapy-authored wheels for a release.
#
# It produces, in the output directory, the pure-python (py3-none-any) wheels for
# flamapy and the flamapy-authored plugins it depends on
# (flamapy-fw, flamapy-fm, flamapy-sat, flamapy-bdd, flamapy-z3, ...).
#
# The flamapy wheel is built from this repository (so the bundle always ships the
# version being released).  The plugin set and their version constraints are read
# straight from that wheel's metadata -- i.e. the `dependencies` declared in
# pyproject.toml -- and handed to `pip download`.  The bundle therefore contains
# exactly what `pip install flamapy==<version>` would resolve, honouring the
# `~=` constraints, and it automatically follows whenever a plugin is added to or
# removed from flamapy's dependencies.  The pure-python build is forced so the
# wheels load in environments such as Pyodide/WASM.  The resulting wheels are
# consumable by any tool that needs the flamapy stack as wheels (the browser IDE,
# offline installers, etc.).
#
# Intentionally NOT included (downstream tools manage these themselves):
#   - third-party deps (uvlparser, afmparser, antlr4, dd, astutils, graphviz, ply)
#   - flamapy-configurator (not published on PyPI)
#   - python-sat (provided by the Pyodide package set)
#   - z3_solver (the prebuilt wasm32 wheel, tied to the Pyodide version)
#
# Usage:
#   ./build_wheels.sh [OUTPUT_DIR]
#
# OUTPUT_DIR defaults to "wheels".
set -euo pipefail

# Resolve the repository root from this script's location so it can be invoked
# from anywhere (it lives under .github/workflows/).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

OUT_DIR="${1:-wheels}"
PYTHON="${PYTHON:-python}"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# 1. Build the flamapy wheel from this repository.
"$PYTHON" -m build --wheel --outdir "$OUT_DIR" "$REPO_ROOT"

FLAMAPY_WHEEL="$(ls "$OUT_DIR"/flamapy-*-py3-none-any.whl | head -n1)"

# 2. Read the flamapy-authored plugin requirements (name + version constraint)
#    straight from the built wheel's metadata, i.e. the dependencies declared in
#    pyproject.toml.  Plugins carrying an environment marker (e.g. the "dev"
#    extras) are skipped.
mapfile -t PLUGIN_SPECS < <("$PYTHON" - "$FLAMAPY_WHEEL" <<'PY'
import sys, zipfile
from email.parser import Parser

with zipfile.ZipFile(sys.argv[1]) as wheel:
    metadata_name = next(n for n in wheel.namelist() if n.endswith(".dist-info/METADATA"))
    metadata = wheel.read(metadata_name).decode()

for requirement in Parser().parsestr(metadata).get_all("Requires-Dist", []):
    name_spec, _, marker = requirement.partition(";")
    name_spec = name_spec.strip()
    if name_spec.startswith("flamapy-") and not marker.strip():
        print(name_spec)
PY
)

if [ "${#PLUGIN_SPECS[@]}" -eq 0 ]; then
  echo "ERROR: no flamapy-* dependencies found in $FLAMAPY_WHEEL metadata" >&2
  exit 1
fi

echo "Resolved plugin requirements from flamapy metadata:"
printf '  %s\n' "${PLUGIN_SPECS[@]}"

# 3. Download the plugin wheels honouring those constraints, forcing the
#    pure-python (py3-none-any) build so they load in Pyodide/WASM.
"$PYTHON" -m pip download --no-deps --only-binary=:all: \
  --platform none --python-version 3.11 --abi none \
  --dest "$OUT_DIR" \
  "${PLUGIN_SPECS[@]}"

# 4. Drop the sdist that `python -m build` may leave behind; ship only wheels.
rm -f "$OUT_DIR"/*.tar.gz

echo ""
echo "Bundle contents ($OUT_DIR):"
ls -1 "$OUT_DIR"/*.whl
