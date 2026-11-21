<sub>Images: Naruto Shippuden © Masashi Kishimoto / Shueisha · TV Tokyo · Pierrot (via Narutopedia and Pinterest).</sub>

# corehost

MiSTer's Main with the frontend in charge, by f3bandit. Part of **Infinite Tsukuyomi** (無限月読, corehost); this is
its ARM side, codename **Fushi Tensei** (不死転生), driven by **Kugutsu no Jutsu** (傀儡の術,
[Coreshell](https://github.com/f3bandit/core_shell)).

![無限月読: every core dreaming MiSTer's Main is still there](https://i.pinimg.com/originals/c9/e2/18/c9e218989c5f8315f85bc178231caa3d.jpg)

*無限月読 (Infinite Tsukuyomi): every core dreams on, sure that MiSTer's Main is still there, while the frontend holds
the screen. Ask it yourself: `infinite_tsukuyomi` on its socket.*

![不死転生: corehost living on inside MiSTer's own Main](https://static.wikia.nocookie.net/naruto/images/6/61/Fushi_Tensei.png/revision/latest?cb=20120509181240)

*不死転生 (Fushi Tensei), Orochimaru's reincarnation: corehost doesn't rewrite MiSTer's Main, it lives on inside it,
and moves into each new Main_MiSTer release. Ask it yourself: `fushi_tensei` on its socket.*

corehost is [Main_MiSTer](https://github.com/MiSTer-devel/Main_MiSTer) as it is upstream (every core, every
system's loading code, CD and disk emulation, the scaler, input, saves), with a local API a frontend (Phosphor,
Console Mode, any other) drives instead of MiSTer's OSD:

- While a frontend is connected and has the screen, MiSTer's menu never opens. The menu button, the controllers
  and every OSD message go to the frontend.
- When no frontend is connected (none started, or it crashed), MiSTer's menu is there as always. Nobody is ever
  locked out.
- Everything the API does calls the function MiSTer's own menu calls: nothing is written twice.

## Building a frontend on corehost

corehost and Coreshell do everything the way stock MiSTer does (docs/stock-behaviour.md), so a frontend only draws its
menus and sends a few commands. Whatever a user installs from Update All or MiSTer Companion then works under it as on
stock MiSTer, with nothing written for it:

1. `hello`, then `screen frontend`: the menu core's screen is yours (a framebuffer the size the kernel says:
   Coreshell's `display/csdisplay.c` opens it, and its `csd_vt_*` calls let scripts and add-ons switch consoles).
2. Games through Coreshell (`launch` on its socket, `/tmp/coreshell.sock`): the core, its settings, cards, achievements.
3. Scripts: `script PATH`. MiSTer's own terminal (`/tmp/script` on tty2), and back with a `script_done` event. Update
   All, its Patreon check included, and every other script behave as from MiSTer's Scripts menu.
4. `subscribe`: the events (core changed, the menu button, pads, files, the display).
5. In a game, the menu button arrives as an event; `ingame on` puts your in-game menu over the game, and `confstr`,
   `opt`, `action` and `reset` give the core's own menu (its options and actions, as MiSTer's OSD shows them).

Cores with their own Main (NBlood, Duke3D, Quake), MiSTer.ini's `main=`, F9, add-ons writing `/dev/MiSTer_cmd` and the
kernel's display after a Linux update are handled underneath.

## The API

Unix socket `/tmp/corehost.sock` (root only), one command per line, one JSON reply per line. The same commands
as Phosphor's Main (`phosphor-main.sock`), so a frontend written for it only changes the socket path.

| Command | What it does |
|---|---|
| `hello` | API version, codename, the upstream Main it was built on |
| `status` | core, menu core or game, OSD open, framebuffer on, who has the screen, the file loaded |
| `script PATH` | (with the screen, in the menu core) run a script as MiSTer's Scripts menu does: `/tmp/script` on tty2, MiSTer's terminal, "Press any key to continue"; then `{"event":"script_done","status":N}` |
| `subscribe` | events to this client (below) |
| `frontend NAME` | the name in every core's OSD: "Return to NAME" on its System page (no core rebuilt), which comes back to the menu core and the frontend's screen. Coreshell's registered frontend (`frontend` on its socket) is used when no client says |
| `osdtext` | the OSD's rows as text (tests) |
| `settings save` / `settings reset` | the core menu's Save settings / Reset settings, as MiSTer's OSD does them (its .CFG; an arcade's DIP switches and NVRAM): for a frontend's own core menu built from `confstr`, `opt` and `action` |
| `cheats` / `cheat N` | the core's cheats as MiSTer's OSD lists them (name, on), and one switched on or off with the OSD's own toggle: a frontend's own Cheats screen |
| `dips` / `dip I M` / `dips apply` | an arcade's DIP switches (name, choices, the one set), one set to choice M, and Reset and apply, as the OSD's DIP switches page does them |
| `screen frontend` / `screen main` | the menu core's screen: the frontend's framebuffer, or MiSTer's menu |
| `sheet on` / `sheet off` | in a game, the menu button goes to the frontend (its in-game menu) |
| `ingame on` / `ingame off` | the frontend's framebuffer over the running game, the controllers to the frontend |
| `ingame osd` | MiSTer's own menu over the game, for what the frontend doesn't do yet |
| `confstr` | the running core's config string, every line (its whole menu), and each line's state as MiSTer's menu shows it (shown, hidden, disabled) |
| `opt O<bits>` / `opt o<bits> [value]` | read a status field, or set it and read it (`opt oFH 2`) |
| `action <line>` | a config string trigger or reset line run as the OSD runs it, each system's handling with it |
| `reset` | the core's own Reset (status bit 0: PSX, Saturn, Mega CD, N64... resets included) |
| `here <file.mgl>` | an MGL's options, file loads, mounts and resets on the running core, no reload |
| `launch <path>` | an .rbf, .mra or .mgl |
| `screenshot` | MiSTer's screenshot of the running game |
| `infinite_tsukuyomi`, `fushi_tensei` | the jutsu: the core dreaming, and the Main corehost lives in |

Events: `core` (a core loaded), `osd` (MiSTer's menu opened or closed), `menu_button`, `pad` (`{"b":"a","p":1}`:
1 pressed, 0 released, 2 held), `ingame`, `file` (a file loaded or an image mounted), `info` (every OSD message).

Coreshell's handoff (the core's settings and INI settings in the launch's MGL, applied in memory, the user's .CFG
and MiSTer.ini never written) is carried as in Phosphor's Main.

### Loading and saving, drawn by the frontend

Main restarts with each core and is busy while it loads a game, so it can't answer on the socket then. A frontend
that draws the loading and saving boxes itself says so in a file instead, and Main writes what to show (ported from
Phosphor's Main):

- The frontend writes its pid to `/tmp/corehost/draws-loading`. With no such frontend running, MiSTer's own boxes show.
- A load over 350 ms: Main writes `/tmp/corehost/loading`, one line `cur max<TAB>title<TAB>file`, as it moves. Title
  `Saving` with `max` 0 is a game's save being written as it's left (no progress known). The file goes at the end.
- The frontend draws its box into the framebuffer, then creates `/tmp/corehost/loading.shown`. Only then does Main
  show the framebuffer, so the TV never shows what was in it before.

### The framebuffer's mode

- A frontend's own mode (`fb_cmd1` with a size or format of its own, e.g. 960x540 scaled up) is kept in
  `/tmp/corehost/fb-mode` and set again when Main restarts for the next core. `fb_cmd1` at the full 32-bit size clears it.
- `565` in `/tmp/corehost/fb-game-fmt`: the framebuffer is 16-bit while a game core runs (the frontend's in-game
  menu). That halves its memory traffic, which a core that works the DDR hard (N64) otherwise contends with: the menu
  jitters over it. The menu core stays 32-bit, and so do scripts' terminals and a CRT terminal. The frontend draws
  565 while `/sys/module/MiSTer_fb/parameters/mode` says so, and removes the file when it stops.

## Which Main runs

corehost stands in for the Main MiSTer.ini names for the menu (`[MiSTer] main=`, or MiSTer). Every core that uses
it stays in corehost. The RetroAchievements cores (`[RA_*] main=MiSTer_RA`) go to MiSTer_RA, as on any MiSTer. A core whose section names another fork with
its own system code still gets that Main, as with stock MiSTer, and the frontend loses corehost's API until the menu
comes back.

## Building

```
./build.sh --shim ../super-memcard/main/patch/main-mister-super-memcard.patch
```

Main_MiSTer at the commit in `UPSTREAM`, the Super MemCard / Coreshell shim, then `corehost.patch`. Out:
`out/MiSTer_corehost` (named as Main forks are, so scripts such as Update All see a MiSTer Main above them). Needs the ARM toolchain on PATH (`arm-none-linux-gnueabihf-gcc` 10.2, as Main_MiSTer).

## Moving to a new Main (a reincarnation)

1. `./build.sh --upstream <new Main_MiSTer commit>`. If it builds, put that commit in `UPSTREAM`, add one to
   `LIVES`, and test on a MiSTer.
2. If the patch doesn't apply, settle the conflicts in `.cache/work`, then make the patch again from there:
   `git -C .cache/work diff <base> -- . ':!corehost_version.h' > corehost.patch` (base: the commit with the shim
   applied).

## Watching upstream

Two daily workflows here open an issue as soon as MiSTer changes something corehost depends on, so the fix is ready
before Update All can install the change:

- **Main watch** (`main-watch.yml`): Main_MiSTer moved past `UPSTREAM`. It tries the shim and corehost.patch on the
  new Main and builds it for ARM, then reports *builds*, *conflicts* (with the files) or *doesn't apply*. Commits that
  touch corehost's files or the display are marked.
- **Kernel watch** (`kernel-watch.yml`): MiSTer's kernel (Linux-Kernel_MiSTer) moved past `KERNEL`. It reports
  changes to the framebuffer driver (screen address, parameters, code), the kernel options frontends rely on (uinput,
  the framebuffer, Bluetooth...), a move to a new kernel line, then input, USB, Wi-Fi/Bluetooth and the rest.

Each issue closes by itself once `UPSTREAM` or `KERNEL` is moved forward. Neither workflow changes or pushes anything.
Coreshell's kernel check on the MiSTer is the safety net for anything that gets through.

## When the watch can't tell

The watch builds the new Main in the cloud. It can't run it, and it can't look at a Main it has no source for. Do
that on your own MiSTer:

1. **The report, locally.** With the ARM toolchain on PATH and the shim from
   [super-memcard](https://github.com/f3bandit/super-memcard) (`main/patch/main-mister-super-memcard.patch`):

   ```
   ./build.sh --shim <shim patch> --upstream <Main_MiSTer commit> > build.log 2>&1; echo $?
   python3 tools/main_watch.py --src .cache/Main_MiSTer --base $(cat UPSTREAM) --head <commit> \
       --build-exit <that exit code> --build-log build.log --shim <shim patch> --report report.md
   ```

   Exit 0 builds, 3 conflicts, 4 the patch doesn't apply (then see *Moving to a new Main* above). The kernel watch's
   report, from the kernel's history since `KERNEL` (no file contents are fetched until a diff needs them):

   ```
   git clone --filter=blob:none --no-checkout --shallow-since=<a date before KERNEL's commit> \
       --branch <KERNEL's branch> https://github.com/MiSTer-devel/Linux-Kernel_MiSTer kernel
   python3 tools/kernel_watch.py --repo kernel --branch <that branch> --report report.md --state state.json
   ```
2. **Run it.** Copy `out/MiSTer_corehost` to `/media/fat/` and choose it the stock way, with `main=MiSTer_corehost`
   in the `[MiSTer]` section of the MiSTer.ini you're testing with (take it out again to go back). Restart.
3. **Check what Coreshell relies on** in that Main, on the MiSTer:

   ```
   cd /media/fat/coreshell
   python3 -m coreshell mains probe /media/fat/MiSTer_corehost --out /tmp/probe.json
   ```

   Every line should say `ok` (load_core, the command pipe, MGL `<setname>` and `<option>`, the `.CFG` name,
   `/tmp/CORENAME`, `main=`). The same works for any other Main, a fork without public source included.
4. **Check corehost's API** with a stand-in frontend (copy `tools/ch.py` and `tools/test_frontend.py` to the MiSTer):
   `python3 test_frontend.py` holds the screen and logs every reply and event to `/tmp/chf.log`, and sends what you
   write to `/tmp/chf.in` (`echo status > /tmp/chf.in`); `python3 ch.py hello status` sends single commands. Both use
   `COREHOST_SOCK` when corehost was started with it. Start a game, read its menu with `python3 ch.py confstr` (it
   needs a game running), press the menu button, come back to the menu.
5. **The kernel:** `python3 -m coreshell kernel check` on the MiSTer says whether the display a frontend needs is
   still there.

Send `report.md`, `/tmp/probe.json` and what you saw in an issue on this repo. A core's menu that the cloud can't read
is read on the MiSTer through Coreshell: [Reading a core or a Main yourself](https://github.com/f3bandit/core_shell/blob/main/docs/MANUAL_DUMPS.md).

## Tools

- `tools/ch.py status reset ...`: send commands and print the replies.
- `tools/kernel_watch.py`, `tools/main_watch.py`: the reports behind the two watches (they run locally too).
- `tools/test_frontend.py`: a stand-in frontend. It holds the screen and the menu button, logs every reply and event
  to `/tmp/chf.log`, reconnects after each core load, and sends the commands written to `/tmp/chf.in`.

## Licence

GPL-3.0 or later (LICENSE), as Main_MiSTer: corehost.patch is a change to Main_MiSTer, by Alexey Melnikov "Sorgelig"
and the MiSTer devs, with the authors its files name. The frontend API is ported from Phosphor's Main (f3bandit). Not
affiliated with or endorsed by the MiSTer project.

The GPL covers corehost itself. Coreshell (Apache-2.0), the rest of Infinite Tsukuyomi and frontends only talk to
corehost over its socket, so they keep their own licences; `tools/` are Apache-2.0 socket clients. Details: NOTICE.
