#!/bin/bash
# RangeTrack WiFi watchdog. Run as root every 2 minutes by
# rangetrack-wifi-watchdog.timer (installed by install_wifi_watchdog.sh).
#
# Why it exists: when a reconnect attempt times out, NetworkManager decides the
# password must be wrong ("no-secrets") and blocks that network from
# auto-connecting. Nothing ever clears that block on a headless unit: there is no
# retry timer for it, and connection.autoconnect-retries doesn't apply to it. So
# the unit sits offline until someone restarts it. Observed on a field unit:
# on 2026-10-16 every attempt after a 4am reboot timed out, both networks were
# blocked by 04:03, and nothing retried for 16 hours; on 2026-10-25 the same thing
# after an 8am restart left it offline ~10 hours. A drop during the WPA handshake
# takes the same path without consulting connection.auth-retries at all
# (nm-device-wifi.c, NetworkManager 1.52), so a setting alone can't cover it.
#
# The timeouts themselves look like the Pi's WiFi chip getting stuck, able to scan
# but not connect: its driver reports every failed connect as status 16 with a
# zero router address, the WiFi screen can't connect either, and a restart fixes
# it at once. So when reconnecting keeps failing, this escalates to doing what a
# restart does to the WiFi, without rebooting.
#
# What it does, only while WiFi is disconnected with nothing in progress:
#   every run (after a grace run)  connect the best saved network in range, a
#                                  manual activation that NetworkManager allows
#                                  even for a blocked network
#   after 3 failed rounds          switch WiFi off for a minute and back on, so
#                                  the router drops its record of the Pi (<= 1 per 30 min)
#   after 6 failed rounds          reset the WiFi chip: reload its driver, which
#                                  reloads the firmware, then restart NetworkManager
#                                  (<= 1 per hour)
# It never touches a working connection and never reboots.
#
#   --dry-run   print the state and what it would do; change nothing

export LC_ALL=C                    # nmcli state names are localized otherwise
export PATH="$PATH:/usr/sbin:/sbin"   # modprobe, rfkill

IFACE="${WATCHDOG_IFACE:-wlan0}"
STATE_FILE="${WATCHDOG_STATE:-/run/rangetrack-wifi-watchdog.state}"   # tmpfs: resets each boot
LOCK_FILE="${WATCHDOG_LOCK:-/run/rangetrack-wifi-watchdog.lock}"
LOG_FILE="${WATCHDOG_LOG:-/home/pi/wifi_watchdog.log}"                 # SD card: survives reboots
SYS_MODULE="${WATCHDOG_SYS_MODULE:-/sys/module}"
SYS_NET="${WATCHDOG_SYS_NET:-/sys/class/net}"

GRACE_RUNS=2              # disconnected this many runs in a row before acting (NM gets first try)
RADIO_CYCLE_AFTER=3       # failed reconnect rounds before switching WiFi off for a minute
CHIP_RESET_AFTER=6        # failed reconnect rounds before resetting the WiFi chip
MAX_CONNECTING_RUNS=8     # ~16 min stuck "connecting" counts as wedged -> chip reset
MAX_UNAVAILABLE_RUNS=5    # wlan0 missing/unavailable this long -> chip reset
RADIO_OFF_SECS=60         # long enough for the router to forget the Pi
RADIO_CYCLE_MIN_GAP=1800  # seconds between WiFi off/on cycles
CHIP_RESET_MIN_GAP=3600   # seconds between chip resets
MAX_CANDIDATES=3          # networks tried per round (each waits up to 45s)
# The Pi 3B+ WiFi driver. brcmfmac_wcc sits on top of brcmfmac, so it must be
# unloaded first; loading brcmfmac normally brings brcmfmac_wcc back by itself.
CHIP_DRIVER=brcmfmac
CHIP_DRIVER_ADDON=brcmfmac_wcc

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

log() {
    local line="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$line"
    [ "$DRY_RUN" -eq 1 ] && return
    echo "$line" >> "$LOG_FILE" 2>/dev/null || return
    # Keep the log bounded on the SD card
    if [ "$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)" -gt 2000 ]; then
        tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp" 2>/dev/null && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
}

# Run a command with a time limit when `timeout` exists (it does on the Pi).
run_limited() {
    local secs="$1"; shift
    if command -v timeout >/dev/null 2>&1; then timeout "$secs" "$@"; else "$@"; fi
}

# nmcli terse output escapes ':' and '\' inside values.
unescape() { sed -e 's/\\:/:/g' -e 's/\\\\/\\/g'; }

# ── State (key=value lines; parsed, never sourced, so a corrupt file can't run code)
offline_runs=0; failed_kicks=0; connecting_runs=0; unavailable_runs=0
offline_since=0; last_radio_cycle=0; last_chip_reset=0
load_state() {
    [ -f "$STATE_FILE" ] || return
    local key val
    while IFS='=' read -r key val; do
        case "$val" in ''|*[!0-9]*) continue ;; esac
        case "$key" in
            offline_runs|failed_kicks|connecting_runs|unavailable_runs|offline_since|last_radio_cycle|last_chip_reset)
                eval "$key=\$val" ;;
        esac
    done < "$STATE_FILE"
}
save_state() {
    [ "$DRY_RUN" -eq 1 ] && return
    printf 'offline_runs=%s\nfailed_kicks=%s\nconnecting_runs=%s\nunavailable_runs=%s\noffline_since=%s\nlast_radio_cycle=%s\nlast_chip_reset=%s\n' \
        "$offline_runs" "$failed_kicks" "$connecting_runs" "$unavailable_runs" "$offline_since" "$last_radio_cycle" "$last_chip_reset" \
        > "$STATE_FILE.tmp" 2>/dev/null && mv "$STATE_FILE.tmp" "$STATE_FILE"
}

# due <last-epoch> <min-gap-seconds>: has enough time passed since <last>?
due() { [ $(( $(date +%s) - $1 )) -ge "$2" ]; }

# connected | connecting | disconnected | unavailable
iface_state() {
    local s
    s=$(run_limited 15 nmcli -t -f DEVICE,STATE device 2>/dev/null \
        | awk -F: -v d="$IFACE" '$1 == d { print $2; exit }')
    case "$s" in
        connected*)   echo connected ;;
        connecting*)  echo connecting ;;
        disconnected) echo disconnected ;;
        *)            echo unavailable ;;   # unavailable, unmanaged, or no such device
    esac
}

# One property of a saved connection, by UUID (so names with spaces/quotes/colons are safe).
prop() { run_limited 10 nmcli -g "$2" connection show uuid "$1" 2>/dev/null | unescape; }

# Saved WiFi networks that are in range (or hidden, so can't be seen in a scan),
# best first the way NetworkManager orders them: priority, then most recently
# used. Lines are "priority<TAB>last_used<TAB>uuid<TAB>name". Profiles set to
# autoconnect=no are left alone.
candidates() {
    local visible uuid ssid prio used
    visible=$(run_limited 15 nmcli -t -f SSID device wifi list ifname "$IFACE" --rescan no 2>/dev/null | unescape)
    run_limited 15 nmcli -t -f UUID,TYPE connection show 2>/dev/null \
        | awk -F: '$2 == "802-11-wireless" { print $1 }' \
        | while read -r uuid; do
            [ -n "$uuid" ] || continue
            [ "$(prop "$uuid" connection.autoconnect)" = "no" ] && continue
            ssid=$(prop "$uuid" 802-11-wireless.ssid)
            if [ "$(prop "$uuid" 802-11-wireless.hidden)" = "yes" ] \
               || { [ -n "$ssid" ] && printf '%s\n' "$visible" | grep -qxF -- "$ssid"; }; then
                prio=$(prop "$uuid" connection.autoconnect-priority)
                used=$(prop "$uuid" connection.timestamp)
                case "$prio" in ''|*[!0-9-]*) prio=0 ;; esac
                case "$used" in ''|*[!0-9]*) used=0 ;; esac
                printf '%s\t%s\t%s\t%s\n' "$prio" "$used" "$uuid" "$(prop "$uuid" connection.id)"
            fi
          done \
        | sort -t "$(printf '\t')" -k1,1nr -k2,2nr
}

# One reconnect round. Returns 0 if a network came up.
kick() {
    local list prio uuid name out tried=0
    if [ "$DRY_RUN" -eq 0 ]; then
        run_limited 20 nmcli device wifi rescan ifname "$IFACE" >/dev/null 2>&1
        sleep 5
    fi
    list=$(candidates)
    if [ -z "$list" ]; then
        log "offline: no saved network in range"
        return 1
    fi
    while IFS="$(printf '\t')" read -r prio _used uuid name; do
        [ -n "$uuid" ] || continue
        [ "$tried" -ge "$MAX_CANDIDATES" ] && break
        tried=$((tried + 1))
        if [ "$DRY_RUN" -eq 1 ]; then
            log "would connect: \"$name\" (priority $prio)"
            continue
        fi
        log "offline: connecting \"$name\" (priority $prio)"
        if out=$(run_limited 60 nmcli --wait 45 connection up uuid "$uuid" 2>&1); then
            log "connected to \"$name\""
            return 0
        fi
        log "  failed: $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-160)"
    done <<EOF
$list
EOF
    [ "$DRY_RUN" -eq 1 ] && return 0
    return 1
}

# Switch WiFi off long enough for the router to drop its record of the Pi, then
# back on: what a restart does to the link, without rebooting. If this run is
# killed while the radio is off, the next run finds it off and turns it back on.
radio_cycle() {
    log "switching WiFi off for ${RADIO_OFF_SECS}s ($1)"
    last_radio_cycle=$(date +%s)
    save_state   # before the long part, so a run cut short still counts toward the limit
    [ "$DRY_RUN" -eq 1 ] && return
    run_limited 15 nmcli radio wifi off
    sleep "$RADIO_OFF_SECS"
    run_limited 15 nmcli radio wifi on
    sleep 10
}

# Reload the WiFi driver, which reloads the chip's firmware: the part of a
# restart that clears a chip stuck able to scan but not connect. Then restart
# NetworkManager, which also clears its "wrong password" blocks.
chip_reset() {
    local had_addon=0 i=0
    log "resetting the WiFi chip ($1)"
    last_chip_reset=$(date +%s)
    save_state   # before the long part, so a run cut short still counts toward the limit
    [ "$DRY_RUN" -eq 1 ] && return
    [ -d "$SYS_MODULE/$CHIP_DRIVER_ADDON" ] && had_addon=1
    for m in "$CHIP_DRIVER_ADDON" "$CHIP_DRIVER"; do
        [ -d "$SYS_MODULE/$m" ] || continue
        run_limited 30 modprobe -r "$m" || log "  could not unload $m"
    done
    sleep 3
    run_limited 30 modprobe "$CHIP_DRIVER" || log "  could not load $CHIP_DRIVER"
    sleep 2
    if [ "$had_addon" -eq 1 ] && [ ! -d "$SYS_MODULE/$CHIP_DRIVER_ADDON" ]; then
        run_limited 30 modprobe "$CHIP_DRIVER_ADDON" || log "  could not load $CHIP_DRIVER_ADDON"
    fi
    while [ ! -e "$SYS_NET/$IFACE" ] && [ "$i" -lt 30 ]; do sleep 1; i=$((i + 1)); done
    if [ -e "$SYS_NET/$IFACE" ]; then
        log "  WiFi chip is back"
    else
        log "  WiFi chip did NOT come back after the reset; only a restart will recover it"
    fi
    rfkill unblock wifi 2>/dev/null
    systemctl restart NetworkManager
}

# ── Main ────────────────────────────────────────────────────────────────────────
if [ "$DRY_RUN" -eq 0 ]; then
    exec 9>"$LOCK_FILE" || exit 0
    command -v flock >/dev/null 2>&1 && { flock -n 9 || exit 0; }
fi
load_state

if ! run_limited 15 nmcli -t general status >/dev/null 2>&1; then
    log "NetworkManager not responding — leaving it to systemd"
    exit 0
fi

# Someone else (the WiFi screen, update.sh) is talking to NetworkManager: stand down.
if pgrep -x nmcli >/dev/null 2>&1; then
    [ "$DRY_RUN" -eq 1 ] && log "another nmcli is running — would stand down"
    exit 0
fi

state=$(iface_state)
now=$(date +%s)
[ "$DRY_RUN" -eq 1 ] && log "dry run: $IFACE is $state (offline_runs=$offline_runs failed_kicks=$failed_kicks)"

case "$state" in
    connected)
        if [ "$offline_since" -gt 0 ]; then
            log "back online (offline ~$(( (now - offline_since) / 60 )) min)"
        fi
        offline_runs=0; failed_kicks=0; connecting_runs=0; unavailable_runs=0; offline_since=0
        if [ "$DRY_RUN" -eq 1 ]; then
            log "connected — nothing to do. If it went offline, it would try:"
            kick
        fi
        ;;
    connecting)
        connecting_runs=$((connecting_runs + 1)); unavailable_runs=0
        [ "$offline_since" -eq 0 ] && offline_since=$now
        if [ "$connecting_runs" -ge "$MAX_CONNECTING_RUNS" ] && due "$last_chip_reset" "$CHIP_RESET_MIN_GAP"; then
            chip_reset "stuck connecting for $connecting_runs runs"
            connecting_runs=0
        fi
        ;;
    disconnected)
        connecting_runs=0; unavailable_runs=0
        offline_runs=$((offline_runs + 1))
        [ "$offline_since" -eq 0 ] && offline_since=$now
        if [ "$offline_runs" -ge "$GRACE_RUNS" ] || [ "$DRY_RUN" -eq 1 ]; then
            if kick; then
                [ "$DRY_RUN" -eq 0 ] && failed_kicks=0
            else
                failed_kicks=$((failed_kicks + 1))
                if [ "$failed_kicks" -ge "$CHIP_RESET_AFTER" ] && due "$last_chip_reset" "$CHIP_RESET_MIN_GAP"; then
                    chip_reset "$failed_kicks reconnect rounds failed"
                    failed_kicks=0
                elif [ "$failed_kicks" -ge "$RADIO_CYCLE_AFTER" ] && due "$last_radio_cycle" "$RADIO_CYCLE_MIN_GAP"; then
                    radio_cycle "$failed_kicks reconnect rounds failed"
                    kick && failed_kicks=0
                fi
            fi
        fi
        ;;
    unavailable)
        unavailable_runs=$((unavailable_runs + 1))
        [ "$offline_since" -eq 0 ] && offline_since=$now
        # A kiosk's WiFi radio should never be off (and a reset wouldn't turn it
        # back on: NetworkManager remembers the radio state).
        if [ "$(run_limited 10 nmcli radio wifi 2>/dev/null)" = "disabled" ]; then
            log "WiFi radio was switched off — turning it on"
            [ "$DRY_RUN" -eq 0 ] && run_limited 10 nmcli radio wifi on
        elif [ "$unavailable_runs" -ge "$MAX_UNAVAILABLE_RUNS" ] && due "$last_chip_reset" "$CHIP_RESET_MIN_GAP"; then
            chip_reset "$IFACE unavailable for $unavailable_runs runs"
            unavailable_runs=0
        fi
        ;;
esac

save_state
exit 0
