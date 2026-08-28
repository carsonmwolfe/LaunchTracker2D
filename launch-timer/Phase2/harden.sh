#!/bin/bash
# RangeTrack — Appliance Hardening (read-only root + watchdog + systemd Flask)
# =============================================================================
# Turns a *working, fully-provisioned* RangeTrack unit into a bulletproof
# appliance that survives yanked power and self-recovers. Run this AFTER setup.sh
# has installed the app and you have confirmed the unit boots and shows the UI.
#
#   sudo bash harden.sh
#   sudo reboot
#
# What it does (idempotent — safe to re-run):
#   1. Creates a dedicated WRITABLE data partition/dir at /data for the files
#      that must survive reboots (settings, unit id, t0 history, logs, cache).
#   2. Migrates any existing settings/identity into /data.
#   3. Installs + enables the systemd unit that supervises Flask (Restart=always,
#      python3 -B so no .pyc is ever written).
#   4. Enables the hardware watchdog (config.txt dtparam + systemd
#      RuntimeWatchdogSec) so a hung Pi reboots itself.
#   5. Enables the READ-ONLY root filesystem overlay (raspi-config do_overlayfs)
#      so power cuts can no longer corrupt the OS or the app.
#
# NOTE: steps 1-4 are reversible and low-risk. Step 5 (overlay) is the one that
# makes the root read-only; after it, code updates require reflashing an image
# (git-OTA is auto-disabled on read-only units — see update.sh / READONLY_IMAGE.md).
#
# UNTESTED-ON-HARDWARE: this script has been static-checked only. The overlay and
# watchdog steps must be verified on a real Pi (see READONLY_IMAGE.md test plan).
set -u

log() { echo "[harden] $*"; }
die() { echo "[harden][FATAL] $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "must run as root (sudo bash harden.sh)"

REPO_DIR="/home/pi/Desktop/LaunchTracker2D"
PHASE2="$REPO_DIR/launch-timer/Phase2"
DATA_DIR="/data/rangetrack"

# Locate config.txt / cmdline.txt across Bookworm/Trixie layouts
BOOT=/boot/firmware
[ -d "$BOOT" ] || BOOT=/boot
CONFIG_TXT="$BOOT/config.txt"
[ -f "$CONFIG_TXT" ] || CONFIG_TXT=/boot/config.txt

# ── Skip everything if already read-only ────────────────────────────────────────
# If the root is already read-only we must NOT try to write to it here. Detect via
# raspi-config's own state check (authoritative), falling back to the mount flags.
ALREADY_RO=0
if command -v raspi-config >/dev/null 2>&1 && raspi-config nonint get_overlay_now >/dev/null 2>&1; then
    ALREADY_RO=1
elif findmnt -no OPTIONS / | grep -qw ro || findmnt -no FSTYPE / | grep -qw overlay; then
    ALREADY_RO=1
fi
if [ "$ALREADY_RO" -eq 1 ]; then
    log "Root filesystem is already READ-ONLY / overlaid. Nothing to do."
    log "To change code: build/reflash a new image (see READONLY_IMAGE.md)."
    exit 0
fi

# =============================================================================
# 1. Writable data area at /data
# =============================================================================
# Design choice: we use a bind-friendly plain directory on a dedicated tmpfs-free
# location. Two supported layouts:
#   (a) A real second partition mounted at /data (preferred for true durability —
#       created at image-build time; see READONLY_IMAGE.md). If /data is already a
#       mountpoint we use it as-is.
#   (b) Fallback: a directory /data on the root partition that is kept WRITABLE by
#       adding it to the overlay's bind-mount exceptions (fstab entry below), so it
#       is excluded from the read-only overlay.
#
# Either way, /data must remain writable after the overlay is enabled. raspi-config
# overlay leaves /boot writable but makes / read-only; a plain /data dir on / would
# become read-only too. So we ensure /data is a separate writable mount.
log "Setting up writable data area at /data ..."
mkdir -p /data "$DATA_DIR"

if mountpoint -q /data; then
    log "/data is already a separate mount — good."
else
    # No dedicated partition. Create a persistent, writable ext4 image file on the
    # boot partition (which raspi-config keeps writable) and loop-mount it at /data
    # via fstab. This survives the read-only root because it is its own filesystem.
    DATA_IMG="$BOOT/rangetrack-data.img"
    if [ ! -f "$DATA_IMG" ]; then
        log "Creating 256MB writable data image at $DATA_IMG ..."
        dd if=/dev/zero of="$DATA_IMG" bs=1M count=256 status=none || die "dd failed"
        mkfs.ext4 -q -F "$DATA_IMG" || die "mkfs.ext4 failed"
    fi
    # fstab entry (idempotent)
    if ! grep -q "rangetrack-data.img" /etc/fstab 2>/dev/null; then
        # $BOOT expands here; the loop image lives on the writable boot partition.
        echo "$DATA_IMG /data ext4 loop,rw,noatime,nofail 0 2" >> /etc/fstab
        log "Added /data loop mount to /etc/fstab"
    fi
    # Mount now so the rest of this script can populate it
    mount /data 2>/dev/null || mount -o loop,rw "$DATA_IMG" /data 2>/dev/null || \
        log "WARNING: could not mount /data now (will mount at boot)"
    mkdir -p "$DATA_DIR"
fi

chown -R pi:pi /data "$DATA_DIR" 2>/dev/null || true
log "Data area ready: $DATA_DIR"

# =============================================================================
# 2. Migrate existing persistent state into /data
# =============================================================================
log "Migrating existing settings/identity into $DATA_DIR ..."
migrate() {  # src dest
    [ -f "$1" ] && [ ! -f "$2" ] && cp -a "$1" "$2" && log "  migrated $(basename "$1")"
}
migrate "$PHASE2/settings.json"                 "$DATA_DIR/settings.json"
migrate "$PHASE2/data_cache.json"               "$DATA_DIR/data_cache.json"
migrate "/home/pi/.rangetrack_unit_id"          "$DATA_DIR/.rangetrack_unit_id"
migrate "/home/pi/.rangetrack_branch"           "$DATA_DIR/.rangetrack_branch"
migrate "/home/pi/.rangetrack_t0_history.json"  "$DATA_DIR/.rangetrack_t0_history.json"
migrate "/home/pi/.rangetrack_last_check"       "$DATA_DIR/.rangetrack_last_check"
migrate "/home/pi/.rangetrack_updates.json"     "$DATA_DIR/.rangetrack_updates.json"
touch "$DATA_DIR/server.log"
chown -R pi:pi "$DATA_DIR" 2>/dev/null || true

# =============================================================================
# 3. systemd-supervised Flask (Restart=always, python3 -B)
# =============================================================================
log "Installing systemd service for Flask ..."
install -m 0644 "$PHASE2/systemd/rangetrack-server.service" \
    /etc/systemd/system/rangetrack-server.service || die "cannot install service"

# Ensure /data is mounted before the service starts.
mkdir -p /etc/systemd/system/rangetrack-server.service.d
cat > /etc/systemd/system/rangetrack-server.service.d/10-data.conf <<'EOF'
[Unit]
RequiresMountsFor=/data
EOF

# Sudoers: start.sh may (re)start the service; allow it without a password.
if ! grep -q "systemctl restart rangetrack-server" /etc/sudoers.d/rangetrack 2>/dev/null; then
    {
        echo 'pi ALL=(ALL) NOPASSWD: /usr/bin/systemctl start rangetrack-server.service'
        echo 'pi ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart rangetrack-server.service'
        echo 'pi ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop rangetrack-server.service'
    } >> /etc/sudoers.d/rangetrack
    log "sudoers updated for rangetrack-server.service"
fi

systemctl daemon-reload
systemctl enable rangetrack-server.service >/dev/null 2>&1 || true
log "Flask service installed + enabled (starts on boot, Restart=always)"

# =============================================================================
# 4. Hardware watchdog
# =============================================================================
log "Enabling hardware watchdog ..."
# 4a. Device tree — expose the BCM watchdog device (/dev/watchdog)
if ! grep -q "^dtparam=watchdog=on" "$CONFIG_TXT" 2>/dev/null; then
    echo "dtparam=watchdog=on" >> "$CONFIG_TXT"
    log "  added dtparam=watchdog=on to $CONFIG_TXT"
fi
# 4b. systemd drives the watchdog: if userspace hangs and systemd stops petting
#     /dev/watchdog, the hardware resets the Pi after RuntimeWatchdogSec.
mkdir -p /etc/systemd/system.conf.d
cat > /etc/systemd/system.conf.d/rangetrack-watchdog.conf <<'EOF'
[Manager]
RuntimeWatchdogSec=15
RebootWatchdogSec=2min
EOF
log "  systemd RuntimeWatchdogSec=15 configured"

# =============================================================================
# 5. Read-only root overlay  (LAST — after this, root is read-only)
# =============================================================================
# We use raspi-config's do_overlayfs, the officially supported path on current
# Pi OS. It builds an initramfs overlay: the real root becomes read-only at the
# block level and all root writes go to a tmpfs upper layer discarded on reboot.
# /boot stays writable (config.txt still editable) and our /data mount stays
# writable (separate filesystem), so app state persists.
if command -v raspi-config >/dev/null 2>&1; then
    log "Enabling read-only root overlay via raspi-config enable_overlayfs ..."
    # enable_overlayfs is the non-interactive function (do_overlayfs is the menu
    # wrapper and would prompt). It rebuilds the initramfs + sets root ro on next
    # boot. We deliberately do NOT enable_bootro: /boot must stay WRITABLE so
    # config.txt is editable and the /data loop image on /boot can be written.
    if raspi-config nonint enable_overlayfs; then
        log "  overlay enabled (takes effect after reboot). /boot left WRITABLE on purpose."
    else
        log "  WARNING: enable_overlayfs returned non-zero — verify manually (see READONLY_IMAGE.md)"
    fi
else
    log "WARNING: raspi-config not found — cannot enable overlay automatically."
    log "         Install raspi-config or enable overlayfs manually (see READONLY_IMAGE.md)."
fi

log ""
log "=== Hardening applied. REBOOT NOW: sudo reboot ==="
log "After reboot the root filesystem is READ-ONLY and self-healing is active."
log "Verify with: findmnt / (should show 'ro') and: sudo systemctl status rangetrack-server"
