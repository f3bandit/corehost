#!/bin/bash
# Build corehost (codename Fushi Tensei): Main_MiSTer at the commit in UPSTREAM, with the Super MemCard / Coreshell shim
# and corehost.patch on top. Out: out/MiSTer_corehost (named as Main forks are, MiSTer_<name>: scripts such as Update All
# look for "/MiSTer" in their Main's command line to know they run under MiSTer's Scripts menu).
#
#   ./build.sh [--shim PATH] [--src DIR] [--upstream SHA]
#     --shim      super-memcard's main/patch/main-mister-super-memcard.patch (default: ../super-memcard/...)
#     --src       a Main_MiSTer clone to use (default: a fresh one in .cache/Main_MiSTer)
#     --upstream  build on another commit (a new reincarnation: see README, "Moving to a new Main")
#
# Needs the ARM toolchain on PATH (arm-none-linux-gnueabihf-gcc 10.2, as Main_MiSTer).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
shim="$here/../super-memcard/main/patch/main-mister-super-memcard.patch"
src="$here/.cache/Main_MiSTer"
upstream=$(cat "$here/UPSTREAM")
while [ $# -gt 0 ]; do
	case "$1" in
		--shim) shim=$2; shift 2 ;;
		--src) src=$2; shift 2 ;;
		--upstream) upstream=$2; shift 2 ;;
		*) echo "unknown option $1" >&2; exit 2 ;;
	esac
done
[ -f "$shim" ] || { echo "no shim patch at $shim (--shim)" >&2; exit 1; }
shim=$(cd "$(dirname "$shim")" && pwd)/$(basename "$shim")   # (the patches are applied from Main's work folder)
command -v arm-none-linux-gnueabihf-gcc >/dev/null || { echo "the ARM toolchain isn't on PATH" >&2; exit 1; }

[ -d "$src/.git" ] || git clone -q https://github.com/MiSTer-devel/Main_MiSTer.git "$src"
work="$here/.cache/work"
rm -rf "$work"
git -C "$src" fetch -q origin
git -C "$src" worktree prune
git -C "$src" worktree add -q --detach "$work" "$upstream"

cd "$work"
apply() { # $1 the patch, $2 its name: a 3-way apply; conflicts are listed (exit 3), a patch that won't apply at all is exit 4
	if git apply --3way "$1" 2> "$here/.cache/apply.log"; then return 0; fi
	if git diff --name-only --diff-filter=U | grep -q .; then
		echo "$2 conflicts with Main_MiSTer ${upstream:0:7} in: $(git diff --name-only --diff-filter=U | tr '\n' ' ')" >&2
		echo "settle them in $work, then make the patch again (README)" >&2
		exit 3
	fi
	echo "$2 doesn't apply to Main_MiSTer ${upstream:0:7}:" >&2
	cat "$here/.cache/apply.log" >&2
	exit 4
}
apply "$shim" "the shim"                 # Super MemCard / Coreshell shim (super-memcard, GPL-3.0)
apply "$here/corehost.patch" "corehost.patch"
printf '#define COREHOST_UPSTREAM "%s"\n#define COREHOST_LIVES %s\n' "${upstream:0:7}" "$(cat "$here/LIVES")" > corehost_version.h
make -j"$(nproc)" > "$here/.cache/make.log" 2>&1 || { echo "the build failed (Main_MiSTer ${upstream:0:7}):" >&2; grep -E "error|Error" "$here/.cache/make.log" | head -20 >&2; tail -5 "$here/.cache/make.log" >&2; exit 5; }
mkdir -p "$here/out"
cp bin/MiSTer "$here/out/MiSTer_corehost"
echo "out/MiSTer_corehost  $(md5sum < "$here/out/MiSTer_corehost" | cut -c1-32)  (Main_MiSTer ${upstream:0:7}, reincarnation $(cat "$here/LIVES"))"
