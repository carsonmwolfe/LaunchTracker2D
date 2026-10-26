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
        *) exit 10 ;;
      esac
      [ -f "$d/$f" ] && cat "$d/$f" | esc || echo ""; exit 0 ;;
  *" connection up uuid "*)
      uuid=${!#}; rc=$(cat "$W/up_rc_$uuid" 2>/dev/null || echo 4)
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
    mkdir -p "$W/sys/module/brcmfmac" "$W/sys/module/brcmfmac_wcc" "$W/sys/module/brcmutil" "$W/sys/class/net/wlan0"
    export WATCHDOG_STATE="$W/wd.state" WATCHDOG_LOCK="$W/wd.lock" WATCHDOG_LOG="$W/wd.log"
    export WATCHDOG_SYS_MODULE="$W/sys/module" WATCHDOG_SYS_NET="$W/sys/class/net"
}
profile() {     # profile <uuid> <name> <ssid> <priority> [timestamp] [autoconnect] [hidden]
    local d="$W/profiles/$1"; mkdir -p "$d"
    echo 802-11-wireless > "$d/type"; echo "$2" > "$d/id"; echo "$3" > "$d/ssid"
    echo "$4" > "$d/priority"; echo "${5:-0}" > "$d/timestamp"
    echo "${6:-yes}" > "$d/autoconnect"; echo "${7:-no}" > "$d/hidden"
}
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

echo "26. nmcli calls the fake didn't understand (would mean a wrong command)"
grep -h "UNHANDLED" "$T"/w*/calls 2>/dev/null | sort -u
check "no unhandled nmcli invocations" "$(cat "$T"/w*/calls | grep -c UNHANDLED)" "0"

echo
echo "passed: $PASS   failed: $FAIL"
[ "$FAIL" -eq 0 ]
