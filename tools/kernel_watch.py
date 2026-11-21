#!/usr/bin/env python3
# Copyright 2026 f3bandit
# SPDX-License-Identifier: Apache-2.0
"""Kernel watch: what MiSTer's Linux kernel (MiSTer-devel/Linux-Kernel_MiSTer) changed since the one corehost and
Coreshell were last checked against (the file KERNEL), sorted by what it can break for a frontend.

A new kernel reaches a MiSTer only when a new MiSTer Linux is released, so this warns before that: the framebuffer
driver (where the screen is and what shape it has), the kernel options Coreshell needs (uinput, the framebuffer,
Bluetooth...), input, USB, Wi-Fi/Bluetooth and the rest. It changes nothing.

  kernel_watch.py --repo DIR --branch NAME [--baseline KERNEL] [--report out.md] [--state out.json]
    --repo    a clone of Linux-Kernel_MiSTer (blobless is enough) with origin/<branch> and the baseline commit
    --branch  the kernel repository's default branch now (MiSTer-vX.Y)
Exit 0 always; the state's "level" says how much it matters: act, look, info or none.
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_URL = "https://github.com/MiSTer-devel/Linux-Kernel_MiSTer"
FB = "drivers/video/fbdev/MiSTer_fb.c"
DEFCONFIG = "arch/arm/configs/MiSTer_defconfig"

# (group, level, path prefixes). The first group a file matches is the one it's counted in.
GROUPS = [
    ("Display (MiSTer_fb, where the screen is and its shape)", "act", [FB]),
    ("Kernel options (MiSTer_defconfig)", "look", [DEFCONFIG]),
    ("Board (device tree)", "look", ["arch/arm/boot/dts/intel/socfpga/socfpga_cyclone5_de10_nano.dts",
                                     "arch/arm/boot/dts/intel/socfpga/socfpga_cyclone5_de10nano.dts",
                                     "arch/arm/boot/dts/intel/socfpga/socfpga_cyclone5.dtsi",
                                     "arch/arm/boot/dts/intel/socfpga/socfpga.dtsi"]),
    ("Input (controllers, keyboards, uinput)", "look", ["drivers/input/", "drivers/hid/"]),
    ("USB", "look", ["drivers/usb/"]),
    ("Bluetooth and Wi-Fi", "look", ["drivers/bluetooth/", "net/bluetooth/", "drivers/net/wireless/"]),
    ("Audio (MiSTer)", "info", ["sound/drivers/MiSTer-audio-spi.c"]),
    ("CPU clock (MiSTer)", "info", ["drivers/clk/socfpga/clk-mister"]),
    ("Storage and filesystems", "info", ["fs/", "drivers/mmc/", "block/"]),
]
OTHER = ("Everything else", "info")

# Options corehost, Coreshell and frontends rely on: one of these going away or changing is "act".
NEEDED = ["CONFIG_FB", "CONFIG_FB_MISTER", "CONFIG_VT", "CONFIG_FRAMEBUFFER_CONSOLE", "CONFIG_INPUT_UINPUT",
          "CONFIG_INPUT_EVDEV", "CONFIG_INPUT_JOYDEV", "CONFIG_HIDRAW", "CONFIG_UHID", "CONFIG_USB_HID", "CONFIG_BT",
          "CONFIG_BLK_DEV_LOOP", "CONFIG_EXT4_FS", "CONFIG_VFAT_FS", "CONFIG_EXFAT_FS", "CONFIG_CIFS"]
LEVELS = ["none", "info", "look", "act"]

def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError("git %s: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout

def show(repo, rev, path):
    r = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (rev, path)], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

def read_baseline(path):
    b = {}
    with open(path) as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                k, _, v = line.partition(" ")
                b[k] = v.strip()
    if "branch" not in b or "commit" not in b:
        raise SystemExit("%s needs 'branch <name>' and 'commit <sha>'" % path)
    return b

def group_of(path):
    for name, level, prefixes in GROUPS:
        if any(path == p or (p.endswith("/") and path.startswith(p)) or path.startswith(p) for p in prefixes):
            return name, level
    return OTHER

def parse_config(text):
    opts = {}
    for line in (text or "").splitlines():
        m = re.match(r"^(CONFIG_\w+)=(.*)$", line)
        if m:
            opts[m.group(1)] = m.group(2)
        m = re.match(r"^# (CONFIG_\w+) is not set$", line)
        if m:
            opts[m.group(1)] = "n"
    return opts

def config_changes(old, new):
    o, n = parse_config(old), parse_config(new)
    out = []
    for k in sorted(set(o) | set(n)):
        a, b = o.get(k, "(unset)"), n.get(k, "(unset)")
        if a != b:
            out.append((k, a, b, k in NEEDED))
    return out

def fb_facts(text):
    """What MiSTer_fb tells a frontend: its parameters and where the screen starts in the reserved memory."""
    if text is None:
        return {"present": False}
    params = sorted(set(re.findall(r"module_param(?:_cb)?\(\s*(\w+)", text)))
    m = re.search(r"smem_start\s*=\s*([^;]+);", text)
    return {"present": True, "params": params, "smem_start": " ".join(m.group(1).split()) if m else None}

def analyse(repo, branch, base):
    head = git(repo, "rev-parse", "origin/" + branch).strip()
    res = {"branch": branch, "head": head, "base_branch": base["branch"], "base": base["commit"],
           "new_line": branch != base["branch"], "commits": [], "groups": {}, "config": [], "fb": {}, "level": "none"}
    if head == base["commit"]:
        return res
    rng = "%s..%s" % (base["commit"], head)
    if res["new_line"]:
        # a new kernel line is rebased on a new Linux: list only MiSTer's own commits on it, compare the trees
        merge_base = git(repo, "merge-base", base["commit"], head, check=False).strip()
        if merge_base:
            rng = "%s..%s" % (merge_base, head)
    log = git(repo, "log", "--no-merges", "--format=%H%x09%h%x09%as%x09%an%x09%s", rng)
    commits = [dict(zip(("sha", "short", "date", "author", "subject"), l.split("\t", 4))) for l in log.splitlines() if l]
    if res["new_line"] and len(commits) > 400:
        commits = []  # the whole of upstream Linux: the tree comparison below is what matters
    for c in commits:
        files = [f for f in git(repo, "show", "--name-only", "--format=", c["sha"]).splitlines() if f]
        c["groups"] = sorted({group_of(f)[0] for f in files})
        c["level"] = max((group_of(f)[1] for f in files), key=LEVELS.index, default="info")
    res["commits"] = commits
    changed = [f for f in git(repo, "diff", "--name-only", base["commit"], head).splitlines() if f]
    for f in changed:
        name, level = group_of(f)
        g = res["groups"].setdefault(name, {"level": level, "files": []})
        g["files"].append(f)
    res["config"] = config_changes(show(repo, base["commit"], DEFCONFIG), show(repo, head, DEFCONFIG))
    old_fb, new_fb = fb_facts(show(repo, base["commit"], FB)), fb_facts(show(repo, head, FB))
    res["fb"] = {"old": old_fb, "new": new_fb, "changed": FB in changed}
    if FB in changed:
        res["fb"]["diff"] = git(repo, "diff", base["commit"], head, "--", FB)
    level = "info"
    for g in res["groups"].values():
        level = max(level, g["level"], key=LEVELS.index)
    if res["new_line"] or old_fb != new_fb or any(n for *_, n in res["config"]):
        level = "act"
    res["level"] = level
    return res

def report(res):
    L = []
    w = L.append
    link = lambda sha, short=None: "[`%s`](%s/commit/%s)" % (short or sha[:7], REPO_URL, sha)
    if res["head"] == res["base"]:
        w("MiSTer's kernel is where it was checked: %s on `%s`. Nothing to do." % (link(res["base"]), res["branch"]))
        return "\n".join(L) + "\n"
    verdict = {"act": "**Needs a change before the next MiSTer Linux** (or a check that it doesn't).",
               "look": "Worth a look: it can change what a frontend sees.",
               "info": "Nothing that touches a frontend."}[res["level"]]
    if res["new_line"]:
        w("**MiSTer's kernel has moved to a new line: `%s`** (checked against `%s`). A new Linux version means new "
          "drivers throughout; the next MiSTer Linux will be built on it." % (res["branch"], res["base_branch"]))
        w("")
    w("Linux-Kernel_MiSTer is at %s on `%s`; corehost and Coreshell were checked against %s (`KERNEL`). %d commit(s). %s"
      % (link(res["head"]), res["branch"], link(res["base"]), len(res["commits"]), verdict))
    w("")
    fb = res["fb"]
    if fb.get("changed") or fb.get("old") != fb.get("new"):
        w("### Display: MiSTer_fb changed")
        o, n = fb["old"], fb["new"]
        if not n.get("present"):
            w("- **MiSTer_fb.c is gone.** The framebuffer frontends draw on would change completely.")
        else:
            if o.get("smem_start") != n.get("smem_start"):
                w("- **Where the screen starts changed:** `%s` → `%s`. corehost's display check (CH_FB_ADDR) and "
                  "Coreshell's kernel probe expect Main's FB_ADDR+4096." % (o.get("smem_start"), n.get("smem_start")))
            added = sorted(set(n.get("params", [])) - set(o.get("params", [])))
            gone = sorted(set(o.get("params", [])) - set(n.get("params", [])))
            if added: w("- New parameters in /sys/module/MiSTer_fb/parameters: %s" % ", ".join("`%s`" % p for p in added))
            if gone: w("- **Parameters gone:** %s (Coreshell reads these)" % ", ".join("`%s`" % p for p in gone))
            if not added and not gone and o.get("smem_start") == n.get("smem_start"):
                w("- Same parameters and screen address; the code changed (diff below).")
        d = fb.get("diff", "")
        if d:
            w("")
            w("<details><summary>MiSTer_fb.c diff (%d lines)</summary>\n\n```diff\n%s\n```\n</details>"
              % (d.count("\n"), "\n".join(d.splitlines()[:400])))
        w("")
    if res["config"]:
        needed = [c for c in res["config"] if c[3]]
        w("### Kernel options")
        if needed:
            w("**Options frontends rely on changed:**")
            for k, a, b, _ in needed:
                w("- `%s`: `%s` → `%s`" % (k, a, b))
            w("")
        other = [c for c in res["config"] if not c[3]]
        if other:
            w("<details><summary>%d other option change(s)</summary>\n" % len(other))
            for k, a, b, _ in other[:300]:
                w("- `%s`: `%s` → `%s`" % (k, a, b))
            w("\n</details>")
        w("")
    if res["groups"]:
        w("### What changed, by area")
        w("| Area | Files | |")
        w("|---|---|---|")
        order = [g[0] for g in GROUPS] + [OTHER[0]]
        for name in sorted(res["groups"], key=order.index):
            g = res["groups"][name]
            w("| %s | %d | %s |" % (name, len(g["files"]), g["level"]))
        w("")
    if res["commits"]:
        w("<details><summary>The commits</summary>\n")
        for c in res["commits"][:200]:
            w("- %s %s (%s, %s) — %s" % (link(c["sha"], c["short"]), c["subject"], c["author"], c["date"],
                                        ", ".join(c["groups"]) or "no files"))
        w("\n</details>")
        w("")
    w("When it's checked (on the SS1 once a MiSTer Linux carries it, or by reading the diff), set `KERNEL` to the new "
      "commit; this issue then closes on the next run.")
    return "\n".join(L) + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--baseline", default=os.path.join(os.path.dirname(HERE), "KERNEL"))
    ap.add_argument("--report")
    ap.add_argument("--state")
    a = ap.parse_args()
    res = analyse(a.repo, a.branch, read_baseline(a.baseline))
    text = report(res)
    if a.report:
        with open(a.report, "w") as f: f.write(text)
    else:
        sys.stdout.write(text)
    if a.state:
        slim = {k: res[k] for k in ("branch", "head", "base_branch", "base", "new_line", "level")}
        slim["commits"] = len(res["commits"])
        with open(a.state, "w") as f: json.dump(slim, f, indent=1)
    return 0

if __name__ == "__main__":
    sys.exit(main())
