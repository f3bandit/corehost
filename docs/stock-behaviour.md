# Stock MiSTer behaviour: the rule

Phosphor, Coreshell and corehost do everything the way stock MiSTer does it: through our Main, core menus and frontend, but
with the same mechanisms. Whatever a user installs from Update All or MiSTer Companion (a core, an add-on, a script, a
utility) then works exactly as on stock, without anything being written for it. Extras are built on top of the stock
mechanism, never in place of it. When stock and ours differ, ours changes.

Before changing how something starts, runs, switches or returns, find how stock Main does it (Main_MiSTer source) and
how the add-on expects it (its source), and match it.

## What Coreshell is for

Coreshell puts the return to the frontend (Phosphor, or any frontend) into stock cores and stock Mains, so no core
and no Main ever has to be recompiled. That is its job. A launch through Coreshell is the stock launch plus that
return, nothing more:

- It never changes a core's settings, video mode, .CFG or INI on its own. The only settings it sends are the ones
  the user chose in a frontend. No profile defaults, no "corrections".
- Whatever our Main or frontend changes for its own screen (16-bit framebuffer, fb modes, OSD) is undone before any
  other Main or core gets the screen, for every core and every Main, not one at a time.
- Game ports and hybrid ARM games run on their own original Mains (with the shim), as stock.
- The only core patch is Super MemCard's, opt-in (core_shell's `corepatch/README.md`); no core is patched for anything else.
- A change that seems to need more than that is discussed before it's made.

A feature that already exists in Phosphor (phosphor-main, the shell) or SS1 Tool is ported from there, not written
again, so it works the same everywhere.

## What stock does, and what we match

| Area | Stock MiSTer | Where we match it |
|---|---|---|
| Scripts | `/tmp/script` (cd to the script's folder, run it, "Press any key to continue"), run by `agetty -a root -l /tmp/script ... tty2`, console switched to tty2 with the framebuffer shown; back to the menu after a key | phosphor-main `phosphor.cpp` script_start; corehost `script` (ported) |
| Scripts that check where they run | Update All: on tty2, a parent whose command line holds `/tmp/script`, and a parent named `MiSTer` or with `/MiSTer` in its command line (`update_all/other.py`, `is_mister_scripts_menu_fb_launch`) | the script file's name; our Mains named `MiSTer_<name>` (MiSTer_phosphor, MiSTer_corehost) |
| F9 | the framebuffer terminal: `chvt 1` and the framebuffer shown (menu core, or a terminal already opened) | Phosphor's Main and corehost pass F9 to the stock handler while another program's console is shown |
| Console switches | Main leaves consoles it didn't open alone; text mode, so any program's `chvt` works | the shell lets switches go (`VT_PROCESS`) and redraws when its console is back; Mains don't take the screen while another program's console (a VT past 2) is in use, or idle less than 3 s |
| `/dev/MiSTer_cmd` | one `read()` is one command, its newline optional (`input.cpp`) | Coreshell's `cmdpipe.py` reads it the same way; what it has nothing to add to goes to Main as sent |
| `load_core` of a core with no profile (a utility: Update All's Linker) | loaded as sent | Coreshell passes it to Main |
| `main=` in MiSTer.ini | the core's Main is started (`app_restart`); the menu goes back to `[MiSTer] main=` | followed; our Mains keep themselves only for `MiSTer`. The game ports (Quake, Duke3D, 3S-ARM, Sonic Mania) and the hybrid platform run their own Mains, with Coreshell's shim where it has one (`mains/`). A hybrid port's core with no `[<core>] main=` of the user's (on or turned off): its installer's line, `main=games/<port>/platform/MiSTer_hybrid`, shown to both Mains in Coreshell's INI view while it starts (a bind mount; MiSTer.ini never written) |
| A core's settings (its `.CFG`, the OSD options) | what the user set in the core's menu, or the core's own default | Coreshell sets only what the user chose in a frontend, nothing else (no profile defaults); every other option stays as the core has it. With nothing chosen the `.CFG` isn't touched |
| A core's own Main returning to the menu (NBlood, Duke3D, Quake, 3S-ARM) | the menu's Main, `[MiSTer] main=` | our Main, when that line names it; Coreshell restarts the frontend's Main if it doesn't |
| An add-on with its own menu that stops Main (DreamSTer) | "Exit To MiSTer": back to MiSTer's menu | Coreshell's `addons/`: its menu names the frontend ("Exit To Phosphor") and it comes back there; `compat/killall`, `pidof`: "MiSTer" is the running Main |
| Any add-on that stops Main, known or not | its own exit | the menu button held 3 s brings the frontend back (Coreshell's takeover.py) |
| Cores in `_Other`, `_Utility`, ... | shown in MiSTer's menu by folder | shown in Phosphor's matching card by folder |

## Never change what nobody chose

A game's settings and picture are the user's. Coreshell, corehost and Phosphor never put a core option, a video setting
or the framebuffer's mode back to a default, or to anything else, unless the user chose it in Coreshell or the
frontend. Whatever a frontend changes for its own screen (Phosphor's 16-bit
menu over a game, its own framebuffer size) is undone before any other Main takes over, so the next Main starts as
stock would, for every Main at once (Phosphor's Main and corehost: `video_fb_handoff()` in `app_restart`). (Nov 16
2026: Quake's picture came up in the wrong colours and low resolution because Phosphor's Main handed the screen over
in its 16-bit game mode; Coreshell was also sending every profile default over the user's own settings.)

## Safety on top (where stock has none)

- A core load waits up to 3 s while a program still writes to the running core through `/dev/mem` (Update All's
  `--blank-display`): the collision freezes the SoC.
- A console switch never waits forever (3 s).
- Coreshell's kernel check, corehost's display check, the upstream watches, update-guard last.
- MiSTer's own updaters from the Scripts folder (Update All, the downloader) run as stock, nothing in them held back;
  a restore point of the system files (Main, the menu core, Linux) is saved first (Coreshell's `bin/run-script`,
  through update-guard), the fallback if an update gets past the watches.

Each of these keeps the stock behaviour and only removes a way for it to fail.
