# RangeTrack — Read-Only Hardened Image

**Status: BUILT, STATIC-CHECKED ONLY. Not yet verified on real hardware.**
Every claim about surviving power loss below MUST be proven with the test plan at
the bottom before this touches a customer unit.

## Why this exists

Field units kept dying from two root causes that no amount of app-level patching
could fix:

1. **SD-card corruption on power loss.** The root filesystem was writable, so every
   unplanned power-off risked corrupting the OS or the app (confirmed: black-screen
   no-boot, and corrupted `.pyc` bytecode killing Flask).
2. **No self-healing.** Flask ran under a shell `nohup`, not a supervisor, so a crash
   left a dead unit until someone physically power-cycled it.

This image makes the OS + app **physically un-writable** and makes every process
**self-recovering**, which is how commercial Pi appliances survive in the field.

## Architecture

| Layer | Mechanism | Effect |
|-------|-----------|--------|
| Read-only root | raspi-config `do_overlayfs` | Power cuts cannot corrupt the OS/app — writes go to a volatile tmpfs upper layer discarded on reboot |
| Persistent data | writable `/data/rangetrack` dir/partition | Settings, unit id, t0 history, logs survive reboots |
| Flask supervision | systemd `rangetrack-server.service`, `Restart=always`, `python3 -B` | Crash/OOM recovers in seconds; `.pyc` files are never written |
| Hung-system recovery | hardware watchdog (`dtparam=watchdog=on` + `RuntimeWatchdogSec`) | A frozen Pi reboots itself |
| Browser | `start.sh` (defers Flask to systemd on hardened units, still supervises the kiosk) | Unchanged UX |

### Backward compatibility (important)

Every code change is gated on whether `/data/rangetrack` exists and is writable
(`HARDENED`). On existing/legacy units and the dev machine it does **not** exist, so:

- `server.py` `DATA_DIR` falls back to `/home/pi` → every persistent file stays
  byte-for-byte where it was.
- `start.sh` keeps launching Flask itself (no systemd service present).
- `update.sh` keeps doing normal git-OTA.

So this branch is safe to run anywhere; hardening only activates on a real image.

## OTA vs. read-only — the key decision

`update.sh` does `git reset --hard`, which writes into the repo. On a read-only
overlay root those writes land in the **tmpfs upper layer and vanish on reboot**.
A git-OTA on a read-only unit is therefore a no-op-until-reboot at best and an
inconsistent half-written tree at worst.

**Decision: read-only units are updated by reflashing a new golden image, not by
pulling code onto a live device** (the professional appliance model). On a
hardened unit `update.sh` auto-disables the destructive git pull and only runs the
safe idempotent provisioning + log rotation.

**Maintainer escape hatch:** `touch /data/rangetrack/.allow_git_ota` lets a single
run pull code onto the live overlay for "try this commit right now" bench testing.
Because the overlay upper layer is tmpfs, that code runs immediately but is
**discarded on the next reboot**. To make a change permanent on the fleet, build
and reflash a new image.

## How to build a hardened unit

1. Flash Raspberry Pi OS Lite (or Desktop) to the SD.
2. Boot, get on the network, `git clone` the repo to
   `/home/pi/Desktop/LaunchTracker2D` and run `setup.sh`. Confirm the unit boots and
   shows the countdown UI normally.
3. Run the hardening (only after the unit is confirmed working):
   ```bash
   sudo bash /home/pi/Desktop/LaunchTracker2D/launch-timer/Phase2/harden.sh
   sudo reboot
   ```
   `harden.sh` is idempotent. Steps 1–4 (data dir, systemd Flask, watchdog) are
   reversible/low-risk; step 5 flips the root to read-only.
4. After reboot, verify (see test plan). Once proven, clone the SD as the golden
   image and flash it to every unit.

To update code on the fleet later: change code → build a fresh golden image →
reflash. Do **not** git-pull onto read-only units.

## Power-cut test plan (RUN THIS BEFORE SHIPPING)

Do all of this on a **bench SD**, never a customer unit.

**A. Self-heal (no power cut needed)**
1. `systemctl status rangetrack-server` → active (running).
2. `sudo systemctl kill -s SIGKILL rangetrack-server` → within ~3s it's running
   again; UI recovers on screen. ✅ proves `Restart=always`.
3. Confirm no `.pyc` under the app tree: `find . -name '*.pyc'` → empty. ✅ proves `-B`.

**B. Read-only root survives yanked power (the main event)**
4. Confirm root is read-only: `findmnt -no OPTIONS /` shows `ro` / overlay; `touch /test`
   fails. ✅
5. Confirm `/data` is writable and holds settings: `touch /data/rangetrack/x && rm` works;
   `ls /data/rangetrack` shows `settings.json`. ✅
6. **Yank power** (pull the plug, don't shut down) while the UI is running. Plug back in.
   Repeat **20 times**. Every boot must return to the countdown UI. Any black screen /
   no-boot = FAIL. ✅ proves corruption immunity.
7. Change a setting (brightness), yank power mid-change, reboot → setting persisted and
   UI healthy. ✅ proves `/data` durability.

**C. Watchdog**
8. Simulate a hang: `sudo bash -c 'echo c > /proc/sysrq-trigger'` (or stress the CPU to
   lockup). The watchdog must reboot the unit within ~15s unattended. ✅

**D. Regression on legacy units (no `/data`)**
9. On a NON-hardened unit (or dev), confirm `HARDENED=False`: settings still read/write
   at `/home/pi`, `update.sh` still git-pulls, `start.sh` still launches Flask. ✅ proves
   the branch is safe to run anywhere.

Only after A–D pass on real hardware should this be promoted toward production.
