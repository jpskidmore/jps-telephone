#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
test "$(uname -m)" = arm64
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
tar -xf 'ThirdParty Sources/pjproject-2.17.tar.gz' -C "$scratch" pjproject-2.17/pjlib/src/pj/os_core_unix.c
source_dir="$scratch/pjproject-2.17"
patch -d "$source_dir" -p1 < ThirdParty/PJSIP/patches/arm64-atomic-alignment.patch
xcrun clang -arch arm64 -mmacosx-version-min=14.0 -O2 -DNDEBUG -DPJ_AUTOCONF=1 \
    -IThirdParty/PJSIP/include -c "$source_dir/pjlib/src/pj/os_core_unix.c" -o "$scratch/os_core_unix.o"
archive=ThirdParty/PJSIP/lib/libpj-arm-apple-darwin.a
cp "$archive" "$scratch/libpj-arm-apple-darwin.a"
xcrun ar -r "$scratch/libpj-arm-apple-darwin.a" "$scratch/os_core_unix.o"
printf 'Rebuilt SHA-256 for %s\n' "$archive"
shasum -a 256 "$scratch/libpj-arm-apple-darwin.a"
cp "$scratch/libpj-arm-apple-darwin.a" "$archive"
