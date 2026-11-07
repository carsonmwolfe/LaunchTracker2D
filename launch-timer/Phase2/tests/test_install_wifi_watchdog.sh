#!/bin/bash
# Tests for install_wifi_watchdog.sh with INSTALL_ROOT pointed at a scratch dir and
# fake sudo/systemctl/nmcli/NetworkManager first on PATH.
#   bash tests/test_install_wifi_watchdog.sh

HERE="$(cd "$(dirname "$0")" && pwd)"
INSTALLER="$HERE/../install_wifi_watchdog.sh"
PHASE2="$(cd "$HERE/.." && pwd)"
PASS=0; FAIL=0
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin"

cat > "$T/bin/sudo" <<'EOF'
#!/bin/bash
[ "$1" = "-n" ] && shift
echo "sudo $*" >> "$W/calls"
[ -f "$W/sudo_denied" ] && { echo "sudo: a password is required" >&2; exit 1; }
exec "$@"
EOF
cat > "$T/bin/systemctl" <<'EOF'
#!/bin/bash
echo "systemctl $*" >> "$W/calls"
case "$1" in
  is-enabled|is-active) [ -f "$W/timer_on" ] ;;
  enable) touch "$W/timer_on" ;;
esac
EOF
cat > "$T/bin/nmcli" <<'EOF'
#!/bin/bash
echo "nmcli $*" >> "$W/calls"
EOF
cat > "$T/bin/NetworkManager" <<'EOF'
#!/bin/bash
# --print-config: echo the key=value lines NetworkManager would have parsed
[ -f "$W/nm_reject" ] && { echo "<error: invalid config>" ; exit 1; }
grep -h '^[a-z].*=' "$INSTALL_ROOT"/etc/NetworkManager/conf.d/*.conf 2>/dev/null
EOF
chmod +x "$T/bin/"*

new_root() {
    W="$T/r$RANDOM$RANDOM"; export W INSTALL_ROOT="$W/root"
    mkdir -p "$INSTALL_ROOT/etc/NetworkManager/conf.d" "$INSTALL_ROOT/etc/systemd/system"; : > "$W/calls"
}
run() { PATH="$T/bin:$PATH" bash "$INSTALLER" > "$W/out" 2>&1; echo $? > "$W/rc"; }
# Privileged calls are recorded twice (by fake sudo, then by the fake command it
# runs); count only the command's own line.
calls() { grep -c -- "^$1" "$W/calls"; }
check() {
    if [ "$2" = "$3" ]; then PASS=$((PASS+1)); echo "  ok    $1"
    else FAIL=$((FAIL+1)); echo "  FAIL  $1"; echo "        expected: [$3]"; echo "        actual:   [$2]"; fi
}
CONF="etc/NetworkManager/conf.d/rangetrack-wifi.conf"
SVC="etc/systemd/system/rangetrack-wifi-watchdog.service"
TMR="etc/systemd/system/rangetrack-wifi-watchdog.timer"

echo "1. fresh install"
new_root; run
check "exit 0" "$(cat "$W/rc")" "0"
check "3 files written" "$(ls "$INSTALL_ROOT/$CONF" "$INSTALL_ROOT/$SVC" "$INSTALL_ROOT/$TMR" 2>/dev/null | wc -l | tr -d ' ')" "3"
check "auth-retries set" "$(grep -c '^connection.auth-retries=10$' "$INSTALL_ROOT/$CONF")" "1"
check "powersave off" "$(grep -c '^wifi.powersave=2$' "$INSTALL_ROOT/$CONF")" "1"
check "service runs the repo's watchdog" "$(grep '^ExecStart=' "$INSTALL_ROOT/$SVC")" "ExecStart=/bin/bash $PHASE2/wifi_watchdog.sh"
check "timer every 2 min after first 1" "$(grep -E '^(OnBootSec|OnUnitInactiveSec)=' "$INSTALL_ROOT/$TMR" | tr '\n' ' ')" "OnBootSec=1min OnUnitInactiveSec=2min "
check "files are 644" "$(find "$INSTALL_ROOT/$CONF" "$INSTALL_ROOT/$SVC" "$INSTALL_ROOT/$TMR" -perm 644 | wc -l | tr -d ' ')" "3"
check "config reloaded once" "$(calls 'nmcli general reload conf')" "1"
check "daemon-reload once" "$(calls 'systemctl daemon-reload')" "1"
check "timer enabled" "$(calls 'systemctl enable --now rangetrack-wifi-watchdog.timer')" "1"
check "reports what it did" "$(tr '\n' '|' < "$W/out")" "wifi watchdog: NetworkManager defaults installed|wifi watchdog: systemd units installed|wifi watchdog: timer enabled|"

echo "2. second run with nothing changed: silent, no reloads"
: > "$W/calls"; run
check "no output" "$(cat "$W/out")" ""
check "no reload / daemon-reload / enable" "$(calls 'nmcli general reload')/$(calls 'systemctl daemon-reload')/$(calls 'systemctl enable')" "0/0/0"

echo "3. someone edits the config by hand -> restored, only NM reloaded"
echo "connection.auth-retries=3" > "$INSTALL_ROOT/$CONF"; : > "$W/calls"; run
check "restored" "$(grep -c '^connection.auth-retries=10$' "$INSTALL_ROOT/$CONF")" "1"
check "NM reload, no daemon-reload" "$(calls 'nmcli general reload conf')/$(calls 'daemon-reload')" "1/0"

echo "4. NetworkManager rejects the config -> backed out, no reload"
new_root; touch "$W/nm_reject"; run
check "config removed" "$([ -e "$INSTALL_ROOT/$CONF" ] && echo present || echo removed)" "removed"
check "no reload" "$(calls 'nmcli general reload conf')" "0"
check "says so" "$(grep -c 'rejected' "$W/out")" "1"
check "units still installed" "$([ -e "$INSTALL_ROOT/$SVC" ] && echo yes)" "yes"

echo "5. no passwordless sudo -> clear messages, nothing written, still exit 0"
new_root; touch "$W/sudo_denied"; run
check "exit 0" "$(cat "$W/rc")" "0"
check "nothing written" "$(ls "$INSTALL_ROOT/etc/NetworkManager/conf.d" "$INSTALL_ROOT/etc/systemd/system" | grep -c rangetrack)" "0"
check "3 write failures reported" "$(grep -c 'could not write' "$W/out")" "3"
check "timer failure reported" "$(grep -c 'could not enable the timer' "$W/out")" "1"

echo "6. timer was disabled later -> re-enabled"
new_root; run; rm -f "$W/timer_on"; : > "$W/calls"; run
check "re-enabled" "$(calls 'systemctl enable --now rangetrack-wifi-watchdog.timer')" "1"
check "files untouched" "$(calls 'daemon-reload')" "0"

echo
echo "passed: $PASS   failed: $FAIL"
[ "$FAIL" -eq 0 ]
