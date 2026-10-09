#!/bin/sh
# Install the pinned verification toolchain (Dafny + Z3) for the current CPU architecture.
# Used by the DevContainer image and by CI. Reads versions and hashes from tools/versions.env.
#   PREFIX (default /opt/provinglangsec) receives: z3/bin/z3 and dotnet-tools/dafny
# Needs: the .NET 8 SDK (`dotnet`), curl, unzip, python3.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../versions.env"
PREFIX=${PREFIX:-/opt/provinglangsec}
case "$(uname -m)" in
  x86_64|amd64)  URL=$Z3_X64_URL;   SHA=$Z3_X64_SHA256 ;;
  aarch64|arm64) URL=$Z3_ARM64_URL; SHA=$Z3_ARM64_SHA256 ;;
  *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;;
esac
mkdir -p "$PREFIX"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

echo "== Z3 $Z3_VERSION ($(uname -m))"
curl -fsSL -o "$TMP/z3.zip" "$URL"
GOT=$(python3 -I -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$TMP/z3.zip")
[ "$GOT" = "$SHA" ] || { echo "Z3 archive hash mismatch: got $GOT, pinned $SHA" >&2; exit 1; }
python3 -I -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$TMP/z3.zip" "$TMP/z3"
rm -rf "$PREFIX/z3"; mkdir -p "$PREFIX/z3"
cp -r "$TMP"/z3/*/bin "$PREFIX/z3/bin"; chmod +x "$PREFIX/z3/bin/z3"
# The archive must really be built for this CPU (a mislabeled archive once shipped an x86-64 binary as "arm64").
python3 -I - "$PREFIX/z3/bin/z3" "$(uname -m)" <<'PY'
import struct, sys
machine = struct.unpack("<H", open(sys.argv[1], "rb").read(20)[18:20])[0]
want = {"x86_64": 62, "amd64": 62, "aarch64": 183, "arm64": 183}[sys.argv[2]]
if machine != want:
    sys.exit(f"Z3 binary has ELF machine {machine}, expected {want} for {sys.argv[2]}")
PY

echo "== Dafny $DAFNY_VERSION"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
rm -rf "$PREFIX/dotnet-tools"
dotnet tool install dafny --version "$DAFNY_VERSION" --tool-path "$PREFIX/dotnet-tools"

"$PREFIX/z3/bin/z3" --version
"$PREFIX/dotnet-tools/dafny" --version
