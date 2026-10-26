#!/bin/bash
set -euo pipefail

if [[ "$(uname -s)" != Darwin ]]; then
	echo "build-redwood.sh requires macOS with Xcode's iPhoneOS SDK" >&2
	exit 2
fi

if [[ $# -ne 2 ]]; then
	echo "usage: $0 PATH_TO_HACKIOS_USERLAND_SRC OUTPUT_DIR" >&2
	exit 2
fi

src_dir=$1
out_dir=$2
mkdir -p "$out_dir"
sdk_path=$(xcrun --sdk iphoneos --show-sdk-path)
clang=$(xcrun --sdk iphoneos --find clang)

"$clang" -arch arm64 -isysroot "$sdk_path" -miphoneos-version-min=16.0 -O1 -dynamiclib \
	-install_name /redwood/lib/libredwood.dylib \
	-framework CoreFoundation -framework IOKit -lobjc \
	-o "$out_dir/libredwood.dylib" "$src_dir/inject.c"

"$clang" -arch arm64 -isysroot "$sdk_path" -miphoneos-version-min=16.0 -O1 -dynamiclib \
	-install_name /redwood/lib/libredwood-sb.dylib \
	-framework CoreFoundation -framework IOKit -lobjc \
	-o "$out_dir/libredwood-sb.dylib" "$src_dir/inject_sb.c"

printf 'SDK: %s\n' "$(xcrun --sdk iphoneos --show-sdk-version)"
file "$out_dir"/*.dylib
lipo -info "$out_dir"/*.dylib
for dylib in "$out_dir"/*.dylib; do
	otool -l "$dylib" | grep -A 5 LC_BUILD_VERSION
done
(cd "$out_dir" && shasum -a 256 *.dylib > SHA256SUMS)
