#!/bin/bash
# Tests for wifi_watchdog.sh against a simulated NetworkManager.
#   bash tests/test_wifi_watchdog.sh
# Fake nmcli/systemctl/pgrep/rfkill/sleep are put first on PATH; every command the
# watchdog issues is recorded in $W/calls so each test can assert what it did.
# Plain bash 3.2 (macOS) as well as bash 5 (the Pi).

HERE="$(cd "$(dirname "$0")" && pwd)"
WATCHDOG="$HERE/../wifi_watchdog.sh"
PASS=0; FAIL=0

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin"

# ── Fake nmcli: reads/writes the simulated world in $W ─────────────────────────
cat > "$T/bin/nmcli" <<'NMCLI'
#!/bin/bash
echo "nmcli $*" >> "$W/calls"
esc() { sed -e 's/\\/\\\\/g' -e 's/:/\\:/g'; }      # nmcli terse escaping
args=" $* "
case "$args" in
  *" device set wlan0 autoconnect "*) echo "${!#}" > "$W/dev_autoconnect"; exit 0 ;;
  *" connection modify --temporary uuid "*)
      [ -f "$W/modify_fails" ] && exit 1
      while [ "$1" != uuid ]; do shift; done; d="$W/profiles/$2"; shift 2
      while [ $# -ge 2 ]; do
        case "$1" in
          802-11-wireless-security.pmf) echo "$2" > "$d/pmf" ;;
          802-11-wireless.cloned-mac-address) printf '%s\n' "$2" > "$d/cloned_mac" ;;
          *) echo "UNHANDLED nmcli modify $1" >> "$W/calls"; exit 99 ;;
        esac
        shift 2
      done
      exit 0 ;;
  *" general status "*) [ -f "$W/nm_running" ] && { echo "connected:full"; exit 0; }; exit 8 ;;
  *" -f DEVICE,STATE device "*)
      if [ "$(cat "$W/radio" 2>/dev/null)" = disabled ]; then echo "wlan0:unavailable"
      elif [ -d "$W/sys/class/net/wlan0" ]; then echo "wlan0:$(cat "$W/state")"; fi
      echo "lo:connected (externally)"; exit 0 ;;
  *" device wifi list "*) cat "$W/visible" 2>/dev/null | esc; exit 0 ;;
  *" device wifi rescan "*) exit 0 ;;
  *" -f UUID,TYPE connection show "*)
      for d in "$W"/profiles/*/; do u=$(basename "$d"); echo "$u:$(cat "$d/type")"; done
      echo "lo-uuid-0000:loopback"; exit 0 ;;
  *" -g "*" connection show uuid "*)
      prop=$2; uuid=${!#}; d="$W/profiles/$uuid"
      case "$prop" in
        connection.id) f=id ;; 802-11-wireless.ssid) f=ssid ;;
        connection.autoconnect-priority) f=priority ;; connection.autoconnect) f=autoconnect ;;
        802-11-wireless.hidden) f=hidden ;; connection.timestamp) f=timestamp ;;
        802-11-wireless-security.key-mgmt) f=keymgmt ;; 802-11-wireless-security.pmf) f=pmf ;;
        802-11-wireless.cloned-mac-address) f=cloned_mac ;;
        *) exit 10 ;;
      esac
      [ -f "$d/$f" ] && cat "$d/$f" | esc || echo ""; exit 0 ;;
  *" connection up uuid "*)
      uuid=${!#}; d="$W/profiles/$uuid"; rc=$(cat "$W/up_rc_$uuid" 2>/dev/null || echo 4)
      # A router that only answers another MAC / only works with PMF off
      [ -f "$W/fixed_by_mac" ] && [ "$(cat "$d/cloned_mac" 2>/dev/null)" = stable ] && rc=0
      [ -f "$W/fixed_by_pmf" ] && [ "$(cat "$d/pmf" 2>/dev/null)" = disable ] && rc=0
      echo "attempt $uuid fwdebug=$(cat "$W/fw_debug" 2>/dev/null) autoconnect=$(cat "$W/dev_autoconnect")" >> "$W/calls"
      if [ "$rc" = 0 ]; then echo connected > "$W/state"; echo "Connection successfully activated"
      else echo "Error: Connection activation failed: (7) Secrets were required, but not provided." >&2; fi
      exit "$rc" ;;
  *" radio wifi on "*) echo enabled > "$W/radio"
      [ -f "$W/fixed_by_radio_cycle" ] && for d in "$W"/profiles/*/; do echo 0 > "$W/up_rc_$(basename "$d")"; done
      exit 0 ;;
  *" radio wifi off "*) echo disabled > "$W/radio"; exit 0 ;;
  *" radio wifi "*) cat "$W/radio" 2>/dev/null || echo enabled; exit 0 ;;
esac
echo "UNHANDLED nmcli $*" >> "$W/calls"; exit 99
NMCLI
cat > "$T/bin/systemctl" <<'EOF'
#!/bin/bash
echo "systemctl $*" >> "$W/calls"
EOF
cat > "$T/bin/pgrep" <<'EOF'
#!/bin/bash
[ -f "$W/other_nmcli" ]
EOF
cat > "$T/bin/rfkill" <<'EOF'
#!/bin/bash
echo "rfkill $*" >> "$W/calls"
EOF
cat > "$T/bin/modprobe" <<'EOF'
#!/bin/bash
# Fake driver: brcmfmac_wcc holds brcmfmac, like the real kernel modules.
echo "modprobe $*" >> "$W/calls"
M="$W/sys/module"; N="$W/sys/class/net"
if [ "$1" = "-r" ]; then
    [ -d "$M/$2" ] || { echo "modprobe: FATAL: Module $2 not found." >&2; exit 1; }
    if [ "$2" = brcmfmac ] && [ -d "$M/brcmfmac_wcc" ]; then
        echo "modprobe: FATAL: Module brcmfmac is in use." >&2; exit 1
    fi
    rmdir "$M/$2"; [ "$2" = brcmfmac ] && rm -rf "$N/wlan0"
    exit 0
fi
mkdir -p "$M/$1"
if [ "$1" = brcmfmac ]; then
    [ -f "$W/no_addon_autoload" ] || mkdir -p "$M/brcmfmac_wcc"
    [ -f "$W/chip_dead" ] || mkdir -p "$N/wlan0"
    [ -f "$W/fixed_by_chip_reset" ] && for d in "$W"/profiles/*/; do echo 0 > "$W/up_rc_$(basename "$d")"; done
fi
exit 0
EOF
cat > "$T/bin/journalctl" <<'EOF'
#!/bin/bash
echo "journalctl $*" >> "$W/calls"
cat "$W/kernel_log" 2>/dev/null
EOF
cat > "$T/bin/sleep" <<'EOF'
#!/bin/bash
# Instant; optionally kills the watchdog during its 60s WiFi-off (simulates being cut short)
if [ "$1" = 60 ] && [ -f "$W/kill_during_radio_off" ]; then rm -f "$W/kill_during_radio_off"; kill -9 $PPID; fi
exit 0
EOF
chmod +x "$T/bin/"*

# ── Helpers ────────────────────────────────────────────────────────────────────
new_world() {   # fresh simulated unit: NM up, wlan0 in state $1
    W="$T/w$RANDOM$RANDOM"; export W
    mkdir -p "$W/profiles"; : > "$W/calls"
    touch "$W/nm_running"; echo "${1:-connected}" > "$W/state"; : > "$W/visible"; echo enabled > "$W/radio"
    echo yes > "$W/dev_autoconnect"
    mkdir -p "$W/sys/module/brcmfmac" "$W/sys/module/brcmfmac_wcc" "$W/sys/module/brcmutil" "$W/sys/class/net/wlan0"
    export WATCHDOG_STATE="$W/wd.state" WATCHDOG_LOCK="$W/wd.lock" WATCHDOG_LOG="$W/wd.log"
    export WATCHDOG_SYS_MODULE="$W/sys/module" WATCHDOG_SYS_NET="$W/sys/class/net"
    # Never the real driver: no debug parameter unless a test creates this file
    export WATCHDOG_FW_DEBUG="$W/fw_debug" WATCHDOG_DIAG_LOG="$W/wd_diag.log"
}
profile() {     # profile <uuid> <name> <ssid> <priority> [timestamp] [autoconnect] [hidden] [key-mgmt]
    local d="$W/profiles/$1"; mkdir -p "$d"
    echo 802-11-wireless > "$d/type"; echo "$2" > "$d/id"; echo "$3" > "$d/ssid"
    echo "$4" > "$d/priority"; echo "${5:-0}" > "$d/timestamp"
    echo "${6:-yes}" > "$d/autoconnect"; echo "${7:-no}" > "$d/hidden"
    echo "${8-wpa-psk}" > "$d/keymgmt"; echo 0 > "$d/pmf"; echo "" > "$d/cloned_mac"
}
offline_20min() {   # state of a unit offline 21+ min, WiFi off/on and chip reset already done
    local n; n=$(date +%s)
    printf 'offline_runs=10\nfailed_kicks=2\noffline_since=%s\nlast_radio_cycle=%s\nlast_chip_reset=%s\n' \
        $((n - 1300)) "$n" "$n" > "$WATCHDOG_STATE"
}
on_break() {        # state of a unit partway through a break
    printf 'break_until=%s\nbreaks=1\noffline_runs=12\noffline_since=%s\n' \
        $(( $(date +%s) + 600 )) $(( $(date +%s) - 1500 )) > "$WATCHDOG_STATE"
}
break_ends() { sed -i.bak "s/^break_until=.*/break_until=$(( $(date +%s) - 1 ))/" "$WATCHDOG_STATE"; }
break_mins() { echo $(( ($(st break_until) - $(date +%s) + 30) / 60 )); }
visible() { printf '%s\n' "$@" > "$W/visible"; }
up_ok()   { echo 0 > "$W/up_rc_$1"; }
run()     { PATH="$T/bin:$PATH" bash "$WATCHDOG" "$@" > "$W/out" 2>&1; }
ups()     { grep -o 'connection up uuid [^ ]*' "$W/calls" | awk '{print $4}' | tr '\n' ' ' | sed 's/ $//'; }
count()   { grep -c -- "$1" "$W/calls"; }
exact()   { grep -cx -- "$1" "$W/calls"; }
radio_cycles() { exact 'nmcli radio wifi off'; }
chip_resets()  { exact 'modprobe brcmfmac'; }
st()      { grep "^$1=" "$WATCHDOG_STATE" 2>/dev/null | cut -d= -f2; }
check() {       # check <description> <actual> <expected>
    if [ "$2" = "$3" ]; then PASS=$((PASS+1)); echo "  ok    $1"
    else FAIL=$((FAIL+1)); echo "  FAIL  $1"; echo "        expected: [$3]"; echo "        actual:   [$2]"; fi
}
field_networks() {   # a real field setup
    profile u24 "HomeNet 2.4" "HomeNet 2.4" 20 1792195000
    profile uent "HomeNet Guest" "HomeNet Guest" 10 1792195800
    profile ux "Phone Hotspot" "Phone Hotspot" 0 1791000000
}

# ── Tests ──────────────────────────────────────────────────────────────────────
echo "1. connected: does nothing"
new_world connected; field_networks; visible "HomeNet 2.4" "HomeNet Guest"
run; run
check "no connection attempts" "$(ups)" ""
check "no restarts" "$(count 'systemctl restart')" "0"
check "offline counter stays 0" "$(st offline_runs)" "0"

echo "2. disconnected: waits one run, then connects the best network in range"
new_world disconnected; field_networks; visible "HomeNet Guest" "HomeNet 2.4" "Neighbor-WiFi"; up_ok u24
run
check "run 1: grace, no attempt" "$(ups)" ""
run
check "run 2: tries highest priority first" "$(ups)" "u24"
check "rescans before choosing" "$(count 'device wifi rescan')" "1"
check "logged success" "$(grep -c 'connected to "HomeNet 2.4"' "$WATCHDOG_LOG")" "1"
run
check "run 3: connected -> counters reset" "$(st offline_runs),$(st failed_kicks)" "0,0"
check "logged back-online" "$(grep -c 'back online' "$WATCHDOG_LOG")" "1"

echo "3. best network fails -> falls back to the next one in the same run"
new_world disconnected; field_networks; visible "HomeNet 2.4" "HomeNet Guest"; up_ok uent
run; run
check "order: 2.4 then Entry" "$(ups)" "u24 uent"
check "failure reason logged" "$(grep -c 'failed: Error: Connection activation failed' "$WATCHDOG_LOG")" "1"
check "failed_kicks not counted on success" "$(st failed_kicks)" "0"

echo "4. equal priority -> most recently used first"
new_world disconnected
profile old "Old" "NetOld" 5 1000; profile new "New" "NetNew" 5 9000; visible NetOld NetNew
run; run
check "newer first" "$(ups)" "new old"

echo "5. saved network not in range -> not attempted"
new_world disconnected; field_networks; visible "Neighbor-WiFi" "SomeoneElse"
run; run
check "no attempts" "$(ups)" ""
check "logs why" "$(grep -c 'no saved network in range' "$WATCHDOG_LOG")" "1"

echo "6. hidden network -> attempted even though a scan can't see it"
new_world disconnected; profile hid "Hidden" "HiddenNet" 0 0 yes yes; visible "Neighbor-WiFi"
run; run
check "hidden attempted" "$(ups)" "hid"

echo "7. autoconnect=no -> left alone"
new_world disconnected; profile manual "Manual" "ManualNet" 50 0 no; profile auto "Auto" "AutoNet" 1
visible ManualNet AutoNet
run; run
check "only the auto profile" "$(ups)" "auto"

echo "8. awkward names: apostrophe, colon, spaces"
new_world disconnected
profile q "I don't know" "I don't know" 3; profile c "Weird:Net" "Weird:Net" 2; profile s "My Home  WiFi" "My Home  WiFi" 1
visible "I don't know" "Weird:Net" "My Home  WiFi"
run; run
check "all three matched, in priority order" "$(ups)" "q c s"
check "name with apostrophe logged intact" "$(grep -c "connecting \"I don't know\"" "$WATCHDOG_LOG")" "1"

echo "9. stuck connecting -> one chip reset, then rate limited"
new_world "connecting (configuring)"; field_networks
i=0; while [ $i -lt 8 ]; do run; i=$((i+1)); done
check "chip reset after 8 runs" "$(chip_resets)" "1"
check "NetworkManager restarted with it" "$(count 'systemctl restart NetworkManager')" "1"
i=0; while [ $i -lt 8 ]; do run; i=$((i+1)); done
check "no second reset within the hour" "$(chip_resets)" "1"

echo "10. WiFi screen (another nmcli) running -> stands down completely"
new_world disconnected; field_networks; visible "HomeNet 2.4"; touch "$W/other_nmcli"
run; run; run
check "no attempts" "$(ups)" ""
check "counters untouched" "$(st offline_runs)" ""

echo "11. every attempt fails -> WiFi off/on after 3 rounds, chip reset after 6, both rate limited"
new_world disconnected; field_networks; visible "HomeNet 2.4" "HomeNet Guest"
i=0; while [ $i -lt 3 ]; do run; i=$((i+1)); done          # grace + 2 failed rounds
check "nothing drastic yet" "$(radio_cycles)/$(chip_resets)" "0/0"
run                                                          # 3rd failed round
check "WiFi switched off and back on" "$(radio_cycles)/$(exact 'nmcli radio wifi on')" "1/1"
check "radio left on" "$(cat "$W/radio")" "enabled"
check "retried straight after the off/on" "$(grep -c 'connecting "HomeNet 2.4"' "$WATCHDOG_LOG")" "4"
i=0; while [ $i -lt 3 ]; do run; i=$((i+1)); done          # rounds 4-6
check "chip reset after 6 rounds" "$(chip_resets)" "1"
check "driver unloaded in the right order, then reloaded" "$(grep -E '^modprobe' "$W/calls" | tr '\n' '|')" "modprobe -r brcmfmac_wcc|modprobe -r brcmfmac|modprobe brcmfmac|"
check "rfkill unblock + NetworkManager restart" "$(exact 'rfkill unblock wifi')/$(count 'systemctl restart NetworkManager')" "1/1"
check "logged the chip came back" "$(grep -c 'WiFi chip is back' "$WATCHDOG_LOG")" "1"
i=0; while [ $i -lt 12 ]; do run; i=$((i+1)); done
check "no repeats inside their limits" "$(radio_cycles)/$(chip_resets)" "1/1"
sed -i.bak "s/^last_radio_cycle=.*/last_radio_cycle=$(( $(date +%s) - 1900 ))/" "$WATCHDOG_STATE"; run
check "WiFi off/on allowed again after 30 min" "$(radio_cycles)" "2"
sed -i.bak "s/^last_chip_reset=.*/last_chip_reset=$(( $(date +%s) - 3700 ))/" "$WATCHDOG_STATE"; run
check "chip reset allowed again after an hour" "$(chip_resets)" "2"

echo "12. NetworkManager not running -> no action"
new_world disconnected; field_networks; visible "HomeNet 2.4"; rm "$W/nm_running"
run; run
check "no attempts" "$(ups)" ""
check "exit quietly with a log line" "$(grep -c 'not responding' "$WATCHDOG_LOG")" "2"

echo "13. wlan0 unavailable"
new_world unavailable; echo disabled > "$W/radio"
run
check "radio off -> turned on" "$(exact 'nmcli radio wifi on')" "1"
new_world unavailable
i=0; while [ $i -lt 5 ]; do run; i=$((i+1)); done
check "radio on but device unavailable for 5 runs -> chip reset" "$(chip_resets)" "1"

echo "14. log stays bounded"
new_world disconnected; field_networks; visible "ATT"
i=0; while [ $i -lt 2500 ]; do echo "old line $i"; i=$((i+1)); done > "$WATCHDOG_LOG"
run; run
lines=$(wc -l < "$WATCHDOG_LOG" | tr -d ' ')
check "trimmed to <=1001 lines" "$([ "$lines" -le 1001 ] && echo yes || echo "no ($lines)")" "yes"

echo "15. corrupt/hostile state file is ignored"
new_world disconnected; field_networks; visible "HomeNet 2.4"
printf 'offline_runs=1;touch %s/pwned\nfailed_kicks=$(touch %s/pwned2)\ngarbage\noffline_runs=1\n' "$W" "$W" > "$WATCHDOG_STATE"
run
check "nothing executed from state file" "$([ -e "$W/pwned" ] || [ -e "$W/pwned2" ] && echo EXECUTED || echo safe)" "safe"
check "valid value still read (1 -> 2 -> acts)" "$(ups)" "u24"

echo "16. replay of 2026-10-16: every attempt fails for 6 rounds, then works"
new_world disconnected; field_networks; visible "HomeNet Guest" "HomeNet 2.4"
i=0; while [ $i -lt 7 ]; do run; i=$((i+1)); done      # grace + 6 failed rounds
check "still offline; 1 WiFi off/on and 1 chip reset so far" "$(cat "$W/state"),$(radio_cycles),$(chip_resets)" "disconnected,1,1"
up_ok u24                                             # it starts working
run
check "reconnects on the next run" "$(cat "$W/state")" "connected"

echo "17. --dry-run changes nothing"
new_world disconnected; field_networks; visible "HomeNet 2.4" "HomeNet Guest"; up_ok u24
run --dry-run
check "no connection up / rescan / restart / driver / radio" "$(ups)|$(count 'device wifi rescan')|$(count 'systemctl')|$(count 'modprobe')|$(count 'radio wifi')" "|0|0|0|0"
check "no state or log written" "$([ -e "$WATCHDOG_STATE" ] || [ -e "$WATCHDOG_LOG" ] && echo written || echo none)" "none"
check "prints the plan" "$(grep -c 'would connect: "HomeNet 2.4"' "$W/out")" "1"
new_world connected; field_networks; visible "HomeNet 2.4"
run --dry-run
check "dry run while connected shows fallback plan" "$(grep -c 'would connect' "$W/out")" "1"

echo "18. at most 3 networks tried per round"
new_world disconnected
for n in 1 2 3 4 5; do profile "p$n" "Net$n" "Net$n" "$n"; done; visible Net1 Net2 Net3 Net4 Net5
run; run
check "3 highest only" "$(ups)" "p5 p4 p3"

echo "19. recovers straight from connecting -> outage still logged"
new_world "connecting (configuring)"; field_networks
run; echo connected > "$W/state"; run
check "back-online line written" "$(grep -c 'back online' "$WATCHDOG_LOG")" "1"
check "no attempts needed" "$(ups)" ""

echo "20. add-on module doesn't come back by itself -> watchdog loads it"
new_world disconnected; field_networks; visible "HomeNet 2.4"; touch "$W/no_addon_autoload"
printf 'failed_kicks=5\noffline_runs=5\n' > "$WATCHDOG_STATE"; run
check "brcmfmac_wcc loaded explicitly" "$(exact 'modprobe brcmfmac_wcc')" "1"
check "both modules present after" "$([ -d "$W/sys/module/brcmfmac" ] && [ -d "$W/sys/module/brcmfmac_wcc" ] && echo yes)" "yes"

echo "21. kernel without the add-on module -> only brcmfmac touched"
new_world disconnected; field_networks; visible "HomeNet 2.4"; rmdir "$W/sys/module/brcmfmac_wcc"; touch "$W/no_addon_autoload"
printf 'failed_kicks=5\noffline_runs=5\n' > "$WATCHDOG_STATE"; run
check "unload/load brcmfmac only" "$(grep -E '^modprobe' "$W/calls" | tr '\n' '|')" "modprobe -r brcmfmac|modprobe brcmfmac|"
check "logged the chip came back" "$(grep -c 'WiFi chip is back' "$WATCHDOG_LOG")" "1"

echo "22. chip doesn't come back -> says so, no reset storm"
new_world disconnected; field_networks; visible "HomeNet 2.4"; touch "$W/chip_dead"
printf 'failed_kicks=5\noffline_runs=5\n' > "$WATCHDOG_STATE"; run
check "logged that only a restart will recover it" "$(grep -c 'did NOT come back' "$WATCHDOG_LOG")" "1"
check "NetworkManager still restarted" "$(count 'systemctl restart NetworkManager')" "1"
i=0; while [ $i -lt 10 ]; do run; i=$((i+1)); done
check "no further resets within the hour" "$(chip_resets)" "1"

echo "23. replay of 2026-10-25: chip stuck until it's reset"
new_world disconnected; field_networks; visible "HomeNet 2.4" "HomeNet Guest"; touch "$W/fixed_by_chip_reset"
n=0; while [ "$(cat "$W/state")" != connected ] && [ $n -lt 20 ]; do run; n=$((n+1)); done
check "back online without a reboot" "$(cat "$W/state")" "connected"
check "8 runs (~16 min): grace, 6 failed rounds + reset, reconnect" "$n" "8"
check "one WiFi off/on, one chip reset" "$(radio_cycles)/$(chip_resets)" "1/1"

echo "24. WiFi off/on is enough -> back in the same run, no chip reset"
new_world disconnected; field_networks; visible "HomeNet 2.4"; touch "$W/fixed_by_radio_cycle"
n=0; while [ "$(cat "$W/state")" != connected ] && [ $n -lt 20 ]; do run; n=$((n+1)); done
check "connected on run 4" "$(cat "$W/state"),$n" "connected,4"
check "no chip reset" "$(chip_resets)" "0"
check "failure counter cleared" "$(st failed_kicks)" "0"

echo "25. cut short while WiFi is off -> turned back on next run, limit still holds"
new_world disconnected; field_networks; visible "HomeNet 2.4"; touch "$W/kill_during_radio_off"
printf 'failed_kicks=2\noffline_runs=3\n' > "$WATCHDOG_STATE"; run
check "run died with WiFi off" "$(cat "$W/radio")" "disabled"
check "off/on was recorded before the long part" "$([ "$(st last_radio_cycle)" -gt 0 ] 2>/dev/null && echo saved || echo lost)" "saved"
run
check "next run turns WiFi back on" "$(cat "$W/radio"),$(exact 'nmcli radio wifi on')" "enabled,1"
run; run; run
check "no second off/on inside 30 min" "$(radio_cycles)" "1"

echo "26. offline 20+ min, every round failing -> PMF off, then a different MAC, then a 15-min break"
new_world disconnected; field_networks; visible "HomeNet 2.4" "HomeNet Guest"; offline_20min
run
check "normal round, then both variants on the best network" "$(ups)" "u24 uent u24 u24"
check "PMF off first, then MAC, then put back" "$(grep -o 'modify --temporary uuid u24 [^ ]*' "$W/calls" | awk '{print $NF}' | tr '\n' ' ')" "802-11-wireless-security.pmf 802-11-wireless.cloned-mac-address 802-11-wireless-security.pmf "
check "profile back as it was" "$(cat "$W/profiles/u24/pmf"),$(cat "$W/profiles/u24/cloned_mac")" "0,"
check "NetworkManager's own attempts paused" "$(cat "$W/dev_autoconnect")" "no"
check "15 min break" "$(break_mins)" "15"
check "logged the break" "$(grep -c 'not trying for 15 min' "$WATCHDOG_LOG")" "1"
check "no WiFi off/on or chip reset" "$(radio_cycles)/$(chip_resets)" "0/0"

echo "27. during the break: no attempts at all"
run; run; run
check "no new attempts" "$(ups)" "u24 uent u24 u24"
check "still paused" "$(cat "$W/dev_autoconnect")" "no"

echo "28. break over, still failing -> tries again; next breaks 30, 60, 60 min"
break_ends; run
check "a normal round and the variants again" "$(ups)" "u24 uent u24 u24 u24 uent u24 u24"
check "pause lifted before retrying (no attempt while paused)" "$(grep -c 'attempt .* autoconnect=no' "$W/calls")" "0"
check "second break 30 min" "$(break_mins)" "30"
break_ends; run
check "third break 60 min" "$(break_mins)" "60"
break_ends; run
check "then 60 min again" "$(break_mins),$(st breaks)" "60,4"
check "no WiFi off/on or chip reset during breaks" "$(radio_cycles)/$(chip_resets)" "0/0"

echo "29. network answers again at a retry -> connected; break state cleared"
up_ok u24; break_ends; run
check "connected" "$(cat "$W/state")" "connected"
run
check "breaks cleared, NetworkManager auto-connect on" "$(st breaks),$(st break_until),$(cat "$W/dev_autoconnect")" "0,0,yes"
check "logged back online after the breaks" "$(grep -c 'back online (offline ~2[0-9] min, after 4 break' "$WATCHDOG_LOG")" "1"

echo "30. router only answers a different MAC -> connects with it and keeps it"
new_world disconnected; field_networks; visible "HomeNet 2.4"; touch "$W/fixed_by_mac"; offline_20min
run
check "connected" "$(cat "$W/state")" "connected"
check "normal, PMF off, different MAC" "$(ups)" "u24 u24 u24"
check "different MAC kept in memory" "$(cat "$W/profiles/u24/cloned_mac")" "stable"
check "logged which one worked" "$(grep -c 'connected to "HomeNet 2.4" with a different MAC address' "$WATCHDOG_LOG")" "1"
check "no break" "$(st break_until)" "0"

echo "31. works with PMF off -> stops there, MAC left alone"
new_world disconnected; field_networks; visible "HomeNet 2.4"; touch "$W/fixed_by_pmf"; offline_20min
run
check "connected after normal + PMF off" "$(cat "$W/state"),$(ups)" "connected,u24 u24"
check "PMF off kept, MAC untouched" "$(cat "$W/profiles/u24/pmf"),$(cat "$W/profiles/u24/cloned_mac")" "disable,"
check "logged" "$(grep -c 'with PMF off (kept until NetworkManager restarts)' "$WATCHDOG_LOG")" "1"

echo "32. open network -> no PMF variant, MAC variant only, then put back"
new_world disconnected; profile op "Cafe" "Cafe" 0 0 yes no ""; visible Cafe; offline_20min
run
check "normal + different MAC" "$(ups)" "op op"
check "PMF never touched" "$(count 'security.pmf')" "0"
check "MAC put back" "$(cat "$W/profiles/op/cloned_mac")" ""

echo "33. nothing saved in range for 20+ min -> no break (it may reappear any minute)"
new_world disconnected; field_networks; visible "Neighbor-WiFi"; offline_20min
run
check "no break, auto-connect left on" "$(st break_until),$(cat "$W/dev_autoconnect")" "0,yes"
check "no variants" "$(count 'modify --temporary')" "0"

echo "34. connected from the WiFi screen during a break -> auto-connect back on"
new_world connected; field_networks; on_break; echo no > "$W/dev_autoconnect"
run
check "auto-connect on, break cleared" "$(cat "$W/dev_autoconnect"),$(st break_until),$(st breaks)" "yes,0,0"

echo "35. NetworkManager restarted during a break -> pause applied again, still no attempts"
new_world disconnected; field_networks; visible "HomeNet 2.4"; on_break
run
check "paused, no attempts" "$(cat "$W/dev_autoconnect"),$(ups)" "no,"

echo "36. driver's own reason saved (at most once per 30 min), debug switched back off"
new_world disconnected; field_networks; visible "HomeNet 2.4"; echo 0 > "$W/fw_debug"
cat > "$W/kernel_log" <<'KLOG'
Nov 05 21:30:01.000001 rangetrack1 kernel: brcmfmac: brcmf_fweh_event_worker event ESCAN_RESULT (69) ifidx 0 bsscfg 0 addr 00:00:00:00:00:00
Nov 05 21:30:01.000002 rangetrack1 kernel: brcmfmac: brcmf_fweh_event_worker   version 2 flags 0 status 8 reason 0
Nov 05 21:30:01.000003 rangetrack1 kernel: brcmfmac: brcmf_cfg80211_escan_handler result for 02:00:00:00:00:b8
Nov 05 21:30:01.000004 rangetrack1 kernel: brcmfmac: brcmf_rx_event Enter: mmc1:0001:1: rxp=fa4e30ec
Nov 05 21:30:01.000005 rangetrack1 kernel: brcmfmac: brcmf_inform_single_bss bssid: 02:00:00:00:00:c1
Nov 05 21:30:01.000006 rangetrack1 kernel: brcmfmac: brcmf_cfg80211_get_station RSSI -42 dBm
Nov 05 21:30:02.100000 rangetrack1 kernel: brcmfmac: brcmf_cfg80211_connect Applied Vndr IEs for Assoc request
Nov 05 21:30:02.400000 rangetrack1 kernel: brcmfmac: brcmf_fweh_event_worker event SET_SSID (0) ifidx 0 bsscfg 0 addr 02:00:00:00:00:b8
Nov 05 21:30:02.400001 rangetrack1 kernel: brcmfmac: brcmf_fweh_event_worker   version 2 flags 0 status 2 reason 0
Nov 05 21:30:02.400100 rangetrack1 kernel: brcmfmac: brcmf_bss_connect_done Report connect result - connection failed
Nov 05 21:30:02.500000 rangetrack1 kernel: usb 1-1.3: some unrelated line
KLOG
run; run
check "debug on for that attempt only" "$(grep -o 'attempt u24 fwdebug=[^ ]*' "$W/calls" | tr '\n' ' ')" "attempt u24 fwdebug=0x8400 "
check "switched back off" "$(cat "$W/fw_debug"),$(st fw_debug_on)" "0,0"
check "firmware status and join event saved" "$(grep -c 'status 2 reason 0' "$W/wd_diag.log"),$(grep -c 'event SET_SSID' "$W/wd_diag.log")" "1,1"
check "connect request and result saved" "$(grep -c 'brcmf_cfg80211_connect Applied' "$W/wd_diag.log"),$(grep -c 'brcmf_bss_connect_done' "$W/wd_diag.log")" "1,1"
check "scan noise and unrelated lines left out" "$(grep -ci 'escan\|status 8\|unrelated\|rx_event\|inform_single_bss\|get_station' "$W/wd_diag.log")" "0"
run
check "not again within 30 min" "$(grep -c 'fwdebug=0x8400' "$W/calls")" "1"

echo "37. run cut short with debug on -> next run turns it off"
new_world connected; echo 33792 > "$W/fw_debug"; printf 'fw_debug_on=1\n' > "$WATCHDOG_STATE"
run
check "debug off" "$(cat "$W/fw_debug"),$(st fw_debug_on)" "0,0"
check "logged" "$(grep -c 'debug log back off' "$WATCHDOG_LOG")" "1"

echo "38. kernel without the debug parameter -> plain attempt, no driver log"
new_world disconnected; field_networks; visible "HomeNet 2.4"
run; run
check "attempted" "$(ups)" "u24"
check "no driver log written" "$([ -e "$W/wd_diag.log" ] && echo written || echo none)" "none"

echo "39. --dry-run during a break changes nothing"
new_world disconnected; field_networks; visible "HomeNet 2.4"; on_break; echo no > "$W/dev_autoconnect"
run --dry-run
check "no NetworkManager changes, no attempts" "$(count 'device set')|$(ups)" "0|"
check "says it's on a break" "$(grep -c 'on a break from trying' "$W/out")" "1"

echo "40. nmcli calls the fake didn't understand (would mean a wrong command)"
grep -h "UNHANDLED" "$T"/w*/calls 2>/dev/null | sort -u
check "no unhandled nmcli invocations" "$(cat "$T"/w*/calls | grep -c UNHANDLED)" "0"

echo
echo "passed: $PASS   failed: $FAIL"
[ "$FAIL" -eq 0 ]
