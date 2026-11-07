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
# The timeouts: the Pi's driver reports every failed connect as status 16 with a
# zero router address, so the logs can't say why. Some cleared with a restart, so
# when reconnecting keeps failing this first does what a restart does to the WiFi.
# But on 2026-10-29 the same field unit lost its network when the router went off
# the air for a few minutes, and then couldn't rejoin it for a week: every attempt
# timed out at the join step, through reboots, WiFi off/on cycles and 142 chip
# resets, while the same Pi joined other networks at once. Every earlier outage
# like this had cleared on the first attempt after hours with nothing retrying
# (NetworkManager had given up); this one, retried every few minutes, never did.
# So after 20 minutes this stops trying for a while, and also tries the network
# with settings the Pi doesn't normally need. Which one worked is logged, and the
# driver's own reason for a failure is saved, so the next outage explains itself.
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
#   after 20 minutes offline       connect the best network with PMF off, then also
#                                  with a different MAC address (in memory only), then
#                                  stop all attempts for 15 min and try again; then
#                                  30 min, then every 60 min
#   at most every 30 minutes       save the driver's reason for one connect attempt
#                                  to /home/pi/wifi_diag.log
# It never touches a working connection and never reboots.
#
#   --dry-run   print the state and what it would do; change nothing

export LC_ALL=C                    # nmcli state names are localized otherwise
export PATH="$PATH:/usr/sbin:/sbin"   # modprobe, rfkill

IFACE="${WATCHDOG_IFACE:-wlan0}"
STATE_FILE="${WATCHDOG_STATE:-/run/rangetrack-wifi-watchdog.state}"   # tmpfs: resets each boot
LOCK_FILE="${WATCHDOG_LOCK:-/run/rangetrack-wifi-watchdog.lock}"
LOG_FILE="${WATCHDOG_LOG:-/home/pi/wifi_watchdog.log}"                 # SD card: survives reboots
DIAG_LOG="${WATCHDOG_DIAG_LOG:-/home/pi/wifi_diag.log}"                # SD card: survives reboots
FW_DEBUG="${WATCHDOG_FW_DEBUG:-/sys/module/brcmfmac/parameters/debug}"
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
BREAK_AFTER_SECS=1200     # offline this long with every round failing -> start taking breaks
BREAK_MINS="15 30 60"     # length of each break from trying, in minutes; the last repeats
# Debug bits for the WiFi driver (EVENT|CONN): it then logs the firmware's own
# status for each connect, which it otherwise throws away when reporting
# "status 16": 1 = refused (reason = the router's 802.11 code), 2 = no answer,
# 3 = network not found, 5 = frames not acknowledged.
FW_DEBUG_LEVEL=0x8400
DIAG_MIN_GAP=1800         # seconds between saved driver logs
# The Pi 3B+ WiFi driver. brcmfmac_wcc sits on top of brcmfmac, so it must be
# unloaded first; loading brcmfmac normally brings brcmfmac_wcc back by itself.
CHIP_DRIVER=brcmfmac
CHIP_DRIVER_ADDON=brcmfmac_wcc

DRY_RUN=0; kick_tried=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

# trim_log <file> <max lines> <lines kept>: keep a log bounded on the SD card
trim_log() {
    [ "$(wc -l < "$1" 2>/dev/null || echo 0)" -gt "$2" ] || return 0
    tail -n "$3" "$1" > "$1.tmp" 2>/dev/null && mv "$1.tmp" "$1"
}

log() {
    local line="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$line"
    [ "$DRY_RUN" -eq 1 ] && return
    echo "$line" >> "$LOG_FILE" 2>/dev/null || return
    trim_log "$LOG_FILE" 2000 1000
}

# Run a command with a time limit when `timeout` exists (it does on the Pi).
run_limited() {
    local secs="$1"; shift
    if command -v timeout >/dev/null 2>&1; then timeout "$secs" "$@"; else "$@"; fi
}

# nmcli terse output escapes ':' and '\' inside values.
unescape() { sed -e 's/\\:/:/g' -e 's/\\\\/\\/g'; }

# ── State (key=value lines; parsed, never sourced, so a corrupt file can't run code)
STATE_KEYS="offline_runs failed_kicks connecting_runs unavailable_runs offline_since last_radio_cycle last_chip_reset break_until breaks last_diag fw_debug_on"
for k in $STATE_KEYS; do eval "$k=0"; done
load_state() {
    [ -f "$STATE_FILE" ] || return
    local key val
    while IFS='=' read -r key val; do
        case "$key" in ''|*[!a-z_]*) continue ;; esac
        case "$val" in ''|*[!0-9]*) continue ;; esac
        case " $STATE_KEYS " in *" $key "*) eval "$key=\$val" ;; esac
    done < "$STATE_FILE"
}
save_state() {
    [ "$DRY_RUN" -eq 1 ] && return
    local k v
    for k in $STATE_KEYS; do eval "v=\$$k"; printf '%s=%s\n' "$k" "$v"; done > "$STATE_FILE.tmp" 2>/dev/null \
        && mv "$STATE_FILE.tmp" "$STATE_FILE"
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

# Turn the driver's debug log on for one connect attempt, then save what the
# firmware said about it. Scan results are left out: they're most of the output.
fw_debug_start() {
    fw_debug_old=$(cat "$FW_DEBUG" 2>/dev/null)
    case "$fw_debug_old" in ''|*[!0-9]*) fw_debug_old=0 ;; esac
    fw_debug_t0=$(date +%s)
    last_diag=$fw_debug_t0; fw_debug_on=1
    save_state   # so the next run turns it off if this one is cut short
    echo "$FW_DEBUG_LEVEL" > "$FW_DEBUG" 2>/dev/null
}
fw_debug_stop() {   # fw_debug_stop <network name> <nmcli exit code>
    echo "$fw_debug_old" > "$FW_DEBUG" 2>/dev/null
    fw_debug_on=0
    {
        echo "=== $(date '+%Y-%m-%d %H:%M:%S') connect \"$1\": nmcli exit $2"
        # An event line and its "version/flags/status/reason" line go together.
        journalctl -k --since "@$fw_debug_t0" --no-pager -o short-precise 2>/dev/null | awk '
            !/brcmf/ { next }
            / event [A-Z_0-9]+ \(/ {
                skip = ($0 ~ / event (ESCAN_RESULT|PFN_NET_FOUND|PFN_NET_LOST|PROBREQ_MSG|IF|RSSI) \(/)
                if (!skip) print
                next
            }
            / version [0-9]+ flags / { if (!skip) print; next }
            { skip = 0 }
            /scan|rx_event Enter|inform_single_bss|inform_bss|get_station|prioritize_acparams/ { next }
            { print }' | tail -n 150
    } >> "$DIAG_LOG" 2>/dev/null
    trim_log "$DIAG_LOG" 4000 2000
}

# One reconnect round. Returns 0 if a network came up; sets kick_tried to the
# number of networks it attempted (0 = none of the saved ones in range).
kick() {
    local list prio uuid name out rc diag tried=0
    kick_tried=0
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
        tried=$((tried + 1)); kick_tried=$tried
        if [ "$DRY_RUN" -eq 1 ]; then
            log "would connect: \"$name\" (priority $prio)"
            continue
        fi
        log "offline: connecting \"$name\" (priority $prio)"
        diag=0
        if [ "$tried" -eq 1 ] && [ -w "$FW_DEBUG" ] && due "$last_diag" "$DIAG_MIN_GAP"; then
            diag=1; fw_debug_start
        fi
        out=$(run_limited 60 nmcli --wait 45 connection up uuid "$uuid" 2>&1); rc=$?
        [ "$diag" -eq 1 ] && fw_debug_stop "$name" "$rc"
        if [ "$rc" -eq 0 ]; then
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

# variant <uuid> <name> <description> <property> <value>: change the profile in
# memory only (NetworkManager forgets it when it restarts), then connect.
variant() {
    local uuid="$1" name="$2" what="$3" out
    shift 3
    log "offline: connecting \"$name\" with $what"
    if ! run_limited 15 nmcli connection modify --temporary uuid "$uuid" "$@" >/dev/null 2>&1; then
        log "  could not change the profile"
        return 1
    fi
    if out=$(run_limited 60 nmcli --wait 45 connection up uuid "$uuid" 2>&1); then
        log "connected to \"$name\" with $what (kept until NetworkManager restarts)"
        return 0
    fi
    log "  failed: $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-160)"
    return 1
}

# The best network again, with settings this Pi doesn't normally need:
#   PMF off            rules out the router offering management-frame protection
#                      in a way this chip mishandles
#   + a different MAC  gets past a router that has stopped answering this Pi's
#                      own address ("stable": the same substitute every time)
# Keeps whichever connects. If neither does, puts the profile back as it was.
try_variants() {
    local best uuid name km old_pmf old_mac
    best=$(candidates | head -n 1)
    uuid=$(printf '%s\n' "$best" | cut -f3)
    name=$(printf '%s\n' "$best" | cut -f4)
    [ -n "$uuid" ] || return 1
    km=$(prop "$uuid" 802-11-wireless-security.key-mgmt)
    if [ "$DRY_RUN" -eq 1 ]; then
        [ "$km" = "wpa-psk" ] && log "would connect: \"$name\" with PMF off"
        log "would connect: \"$name\" with a different MAC address"
        return 1
    fi
    old_mac=$(prop "$uuid" 802-11-wireless.cloned-mac-address)
    if [ "$km" = "wpa-psk" ]; then
        old_pmf=$(prop "$uuid" 802-11-wireless-security.pmf)
        variant "$uuid" "$name" "PMF off" 802-11-wireless-security.pmf disable && return 0
    fi
    variant "$uuid" "$name" "a different MAC address" 802-11-wireless.cloned-mac-address stable && return 0
    if [ "$km" = "wpa-psk" ]; then
        run_limited 15 nmcli connection modify --temporary uuid "$uuid" \
            802-11-wireless-security.pmf "${old_pmf:-0}" 802-11-wireless.cloned-mac-address "$old_mac" >/dev/null 2>&1
    else
        run_limited 15 nmcli connection modify --temporary uuid "$uuid" \
            802-11-wireless.cloned-mac-address "$old_mac" >/dev/null 2>&1
    fi
    return 1
}

# Stop every attempt for a while, NetworkManager's own included: the device's
# autoconnect flag, which NetworkManager forgets when it restarts, so a break
# can't outlive the watchdog. The WiFi screen can still connect during a break.
start_break() {
    local mins n=0 m
    for m in $BREAK_MINS; do mins=$m; [ "$n" -eq "$breaks" ] && break; n=$((n + 1)); done
    log "still offline after $(( (now - offline_since) / 60 )) min: not trying for $mins min (earlier outages like this cleared after a break)"
    [ "$DRY_RUN" -eq 1 ] && return
    breaks=$((breaks + 1))
    break_until=$(( $(date +%s) + mins * 60 ))
    save_state
    run_limited 15 nmcli device set "$IFACE" autoconnect no >/dev/null 2>&1
}
end_break() {
    break_until=0
    [ "$DRY_RUN" -eq 1 ] && return
    run_limited 15 nmcli device set "$IFACE" autoconnect yes >/dev/null 2>&1
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

# A run cut short while the driver's debug log was on: turn it off.
if [ "$fw_debug_on" -eq 1 ] && [ "$DRY_RUN" -eq 0 ]; then
    echo 0 > "$FW_DEBUG" 2>/dev/null
    fw_debug_on=0; save_state
    log "turned the WiFi driver's debug log back off (the last run was cut short)"
fi

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
[ "$DRY_RUN" -eq 1 ] && log "dry run: $IFACE is $state (offline_runs=$offline_runs failed_kicks=$failed_kicks breaks=$breaks)"

case "$state" in
    connected)
        if [ "$offline_since" -gt 0 ]; then
            if [ "$breaks" -gt 0 ]; then
                log "back online (offline ~$(( (now - offline_since) / 60 )) min, after $breaks break(s) from trying)"
            else
                log "back online (offline ~$(( (now - offline_since) / 60 )) min)"
            fi
        fi
        # e.g. connected from the WiFi screen during a break
        if [ "$break_until" -gt 0 ] || [ "$breaks" -gt 0 ]; then end_break; fi
        offline_runs=0; failed_kicks=0; connecting_runs=0; unavailable_runs=0; offline_since=0; breaks=0
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
        if [ "$break_until" -gt "$now" ]; then
            # On a break: no attempts. Re-assert in case NetworkManager restarted.
            if [ "$DRY_RUN" -eq 1 ]; then
                log "on a break from trying: $(( (break_until - now + 59) / 60 )) min left"
            else
                run_limited 15 nmcli device set "$IFACE" autoconnect no >/dev/null 2>&1
            fi
        elif [ "$break_until" -gt 0 ]; then
            end_break
            log "break over: trying again"
            if kick || try_variants; then
                [ "$DRY_RUN" -eq 0 ] && failed_kicks=0
            elif [ "$kick_tried" -gt 0 ]; then
                start_break
            fi   # nothing saved in range: back to checking every run, no break
        elif [ "$offline_runs" -ge "$GRACE_RUNS" ] || [ "$DRY_RUN" -eq 1 ]; then
            if kick; then
                [ "$DRY_RUN" -eq 0 ] && failed_kicks=0
            else
                failed_kicks=$((failed_kicks + 1))
                if [ $(( now - offline_since )) -ge "$BREAK_AFTER_SECS" ] && [ "$kick_tried" -gt 0 ]; then
                    try_variants || start_break
                elif [ "$failed_kicks" -ge "$CHIP_RESET_AFTER" ] && due "$last_chip_reset" "$CHIP_RESET_MIN_GAP"; then
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
