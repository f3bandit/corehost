#!/usr/bin/env python3
# Copyright 2026 f3bandit
# SPDX-License-Identifier: Apache-2.0
"""Main watch report: the commits MiSTer's Main has beyond the one corehost is built on (UPSTREAM), which of them touch
files corehost or the shim change, which touch the display, and how the trial build went (build.sh's exit code).

  main_watch.py --src DIR --base SHA --head SHA --build-exit N --build-log FILE [--report out.md]
Exit 0 always.
"""
import argparse, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = "https://github.com/MiSTer-devel/Main_MiSTer"
DISPLAY = re.compile(r"(^|/)(video|fpga_io|osd|scaler|shmem)\.(cpp|h)$")
BUILD = {0: "built", 3: "CONFLICTS", 4: "PATCH DOESN'T APPLY"}

def patched_files(path):
    try:
        with open(path) as f:
            return {m.group(1) for m in re.finditer(r"^diff --git a/(\S+) ", f.read(), re.M)}
    except OSError:
        return set()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--build-exit", type=int, required=True)
    ap.add_argument("--build-log", required=True)
    ap.add_argument("--shim", default="")
    ap.add_argument("--report")
    a = ap.parse_args()
    ours = patched_files(os.path.join(ROOT, "corehost.patch"))
    shim = patched_files(a.shim) if a.shim else set()
    git = lambda *x: subprocess.run(["git", "-C", a.src] + list(x), capture_output=True, text=True).stdout
    log = git("log", "--no-merges", "--format=%H%x09%h%x09%as%x09%an%x09%s", "%s..%s" % (a.base, a.head))
    rows, hit_ours, hit_display = [], 0, 0
    for line in log.splitlines():
        sha, short, date, author, subject = line.split("\t", 4)
        files = [f for f in git("show", "--name-only", "--format=", sha).splitlines() if f]
        tags = []
        if any(f in ours for f in files): tags.append("**corehost's files**"); hit_ours += 1
        if any(f in shim for f in files): tags.append("the shim's files")
        if any(DISPLAY.search(f) for f in files): tags.append("**display**"); hit_display += 1
        rows.append("- [`%s`](%s/commit/%s) %s (%s, %s)%s" % (short, REPO, sha, subject, author, date,
                                                            " — " + ", ".join(tags) if tags else ""))
    try:
        blog = open(a.build_log, errors="replace").read()
    except OSError:
        blog = ""
    build = BUILD.get(a.build_exit, "FAILED (exit %d)" % a.build_exit)
    L = []
    w = L.append
    w("MiSTer's Main is at [`%s`](%s/commit/%s); corehost is built on [`%s`](%s/commit/%s) (`UPSTREAM`). **%d** new commit(s): "
      "%d touch files corehost changes, %d touch the display." % (a.head[:7], REPO, a.head, a.base[:7], REPO, a.base,
                                                                 len(rows), hit_ours, hit_display))
    w("")
    w("| Trial build (shim + corehost.patch on the new Main, ARM) |")
    w("|---|")
    w("| %s |" % build)
    w("")
    if a.build_exit != 0:
        w("<details><summary>Build output (end)</summary>\n\n```\n%s\n```\n</details>\n" % "\n".join(blog.splitlines()[-40:]))
    w("<details><summary>The new commits</summary>\n")
    L.extend(rows[:200])
    w("\n</details>\n")
    w("To move corehost onto it: `./build.sh --upstream %s`, settle any conflicts, regenerate corehost.patch, set "
      "`UPSTREAM`, add one to `LIVES` (README, \"Moving to a new Main\"). This issue closes on the next run after." % a.head[:7])
    text = "\n".join(L) + "\n"
    if a.report:
        open(a.report, "w").write(text)
    else:
        sys.stdout.write(text)
    return 0

if __name__ == "__main__":
    sys.exit(main())
