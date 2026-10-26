#!/bin/bash
# Installs the WiFi watchdog (see wifi_watchdog.sh for why) plus NetworkManager
# defaults that make it rarely needed. Called by setup.sh and by update.sh every
# hour. Idempotent and quiet: a file is rewritten only when its content changed,
# and nothing is printed unless something changed or failed.
#
# Global NetworkManager defaults, not per-network settings, on purpose: the WiFi
# screen deletes and recreates a network when you connect to it, which throws
# away anything set on the old profile.

PHASE2="$(cd "$(dirname "$0")" && pwd)"
ROOT="${INSTALL_ROOT:-}"   # empty on a unit; a scratch dir in tests
SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo -n"
CHANGED_UNITS=0
CHANGED_NM=0

# install_if_changed <dest> <mode>   (new content on stdin) -> 0 if written
install_if_changed() {
    local tmp rc=1
    tmp=$(mktemp) || return 1
    cat > "$tmp"
    if ! cmp -s "$tmp" "$1" 2>/dev/null; then
        if $SUDO install -m "$2" "$tmp" "$1"; then rc=0
        else echo "wifi watchdog: could not write $1 (needs passwordless sudo)"; rc=2; fi
    fi
    rm -f "$tmp"
    return $rc
}

NM_CONF="$ROOT/etc/NetworkManager/conf.d/rangetrack-wifi.conf"
install_if_changed "$NM_CONF" 644 <<'CONF' && CHANGED_NM=1
# Managed by RangeTrack (install_wifi_watchdog.sh); local edits are overwritten.
[connection]
# A WiFi association that times out is retried this many times before
# NetworkManager blocks the network as "no-secrets" (default 3, about 75s).
# Rides out a router that is slow to accept after a reboot; wifi_watchdog.sh
# covers what this can't (a drop during the WPA handshake skips this counter).
connection.auth-retries=10
# WiFi power-save off on every network, including ones the WiFi screen
# recreates. Replaces the dispatcher script, which needs `iw` (not installed).
wifi.powersave=2
CONF

install_if_changed "$ROOT/etc/systemd/system/rangetrack-wifi-watchdog.service" 644 <<UNIT && CHANGED_UNITS=1
[Unit]
Description=RangeTrack WiFi watchdog (reconnects when NetworkManager has given up)
After=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/bin/bash $PHASE2/wifi_watchdog.sh
TimeoutStartSec=600
Nice=10
UNIT

install_if_changed "$ROOT/etc/systemd/system/rangetrack-wifi-watchdog.timer" 644 <<'UNIT' && CHANGED_UNITS=1
[Unit]
Description=Run the RangeTrack WiFi watchdog every 2 minutes

[Timer]
OnBootSec=3min
OnUnitInactiveSec=2min

[Install]
WantedBy=timers.target
UNIT

if [ "$CHANGED_NM" -eq 1 ]; then
    # Never leave NetworkManager with a config it can't read: check it parses and
    # took effect, and back the file out if not. Reload only rereads the config;
    # it doesn't touch the current connection.
    if $SUDO NetworkManager --print-config 2>/dev/null | grep -q '^connection.auth-retries=10$'; then
        $SUDO nmcli general reload conf >/dev/null 2>&1
        echo "wifi watchdog: NetworkManager defaults installed"
    else
        $SUDO rm -f "$NM_CONF"
        echo "wifi watchdog: NetworkManager rejected $NM_CONF; removed it"
    fi
fi

if [ "$CHANGED_UNITS" -eq 1 ]; then
    $SUDO systemctl daemon-reload
    echo "wifi watchdog: systemd units installed"
fi
if ! systemctl is-enabled --quiet rangetrack-wifi-watchdog.timer 2>/dev/null \
   || ! systemctl is-active --quiet rangetrack-wifi-watchdog.timer 2>/dev/null; then
    $SUDO systemctl enable --now rangetrack-wifi-watchdog.timer >/dev/null 2>&1 \
        && echo "wifi watchdog: timer enabled" \
        || echo "wifi watchdog: could not enable the timer"
fi
exit 0
