#!/bin/sh
# Switch the Sharp TV's Live TV (DVB-S) to programme number $1. Runs as pi (adb key owner).
TV=192.168.178.195:5555
n="$1"
case "$n" in ''|*[!0-9]*) echo "bad number" >&2; exit 2;; esac
[ ${#n} -le 4 ] || { echo "bad number" >&2; exit 2; }
exec 9>/tmp/tv_tune.lock
flock -w 20 9 || { echo "busy" >&2; exit 3; }
adb connect $TV >/dev/null 2>&1
adb -s $TV shell echo ok 2>/dev/null | grep -q ok || { echo "TV unreachable" >&2; exit 4; }
if ! adb -s $TV shell dumpsys window | grep mCurrentFocus | grep -q tvcenter; then
    adb -s $TV shell am start -a com.mediatek.tv.action.TUNER_TYPE \
        -n com.mediatek.tv.oneworld.tvcenter/.nav.TurnkeyUiMainActivity --ei tunerType 2 >/dev/null
    sleep 6
fi
keys=""
for d in $(echo "$n" | sed 's/./& /g'); do keys="$keys KEYCODE_$d"; done
adb -s $TV shell input keyevent $keys
echo "$n" > /var/lib/tvremote/current 2>/dev/null
echo ok
