#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot — dispctl MQTT daemon mit Auto-Restart
# Wird bei Gerätestart automatisch von Termux:Boot ausgeführt.
# Benötigt: Termux + Termux:Boot (F-Droid)

BINARY=/data/local/tmp/dispctl
BROKER=192.168.178.218
PREFIX=tv/display
LOGFILE=/data/local/tmp/dispctl.log

# Warte kurz bis Netzwerk bereit
sleep 8

# SSH-Daemon starten
sshd
echo "[$(date)] sshd gestartet (Port 8022)" >> "$LOGFILE"

echo "[$(date)] dispctl MQTT daemon gestartet" >> "$LOGFILE"

while true; do
    echo "[$(date)] Starte: $BINARY --mqtt $BROKER $PREFIX" >> "$LOGFILE"
    "$BINARY" --mqtt "$BROKER" "$PREFIX" >> "$LOGFILE" 2>&1
    EXIT=$?
    echo "[$(date)] Beendet mit Code $EXIT, Neustart in 5s ..." >> "$LOGFILE"
    sleep 5
done
