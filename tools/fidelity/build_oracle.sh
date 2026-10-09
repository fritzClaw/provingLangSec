#!/bin/sh
# Build the SQLite oracle (debug build with tree tracing) into build/fidelity/oracle.
# The amalgamation is downloaded from sqlite.org and checked against the SHA3-256 hash that
# sqlite.org publishes on https://www.sqlite.org/download.html; a mismatch aborts the build.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
. "$HERE/sqlite.env"
OUT="$ROOT/build/fidelity"
mkdir -p "$OUT"
if [ ! -f "$OUT/sqlite-amalgamation-$SQLITE_NUM/sqlite3.c" ]; then
  curl -fsSL -o "$OUT/amalgamation.zip" "https://www.sqlite.org/$SQLITE_YEAR/sqlite-amalgamation-$SQLITE_NUM.zip"
  GOT=$(python3 -I -c "import hashlib,sys; print(hashlib.sha3_256(open(sys.argv[1],'rb').read()).hexdigest())" "$OUT/amalgamation.zip")
  [ "$GOT" = "$SQLITE_SHA3_256" ] || { echo "SQLite amalgamation hash mismatch: $GOT" >&2; exit 1; }
  python3 -I -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$OUT/amalgamation.zip" "$OUT"
fi
cc -O1 -w -DSQLITE_DEBUG -DSQLITE_ENABLE_TREETRACE -DSQLITE_THREADSAFE=0 \
   -I"$OUT/sqlite-amalgamation-$SQLITE_NUM" -o "$OUT/oracle" "$HERE/oracle.c" -lm -ldl
echo "built $OUT/oracle (SQLite $SQLITE_VERSION, SQLITE_DEBUG + TREETRACE)"
