#!/bin/sh
# EPG for Kodi and the web pages: grab guides for our channels with the iptv-org grabber
# (pass 1: best site, pass 2: next site for channels without programmes) -> m3u/epg.xml.gz + epg_now.json
set -e
cd /home/pi/tvrestore
G=/home/pi/epg
python3 epg_channels.py guides.json $G/heissa1.channels.xml m3u/de/all.m3u > /dev/null
(cd $G && npm run grab --silent -- --channels=heissa1.channels.xml --output=/tmp/epg1.xml --days=2 --maxConnections=4 > /tmp/epg_grab1.log 2>&1) || true
grep -oE '<programme [^>]*channel="[^"]*"' /tmp/epg1.xml | grep -oE 'channel="[^"]*"' | cut -d'"' -f2 | sort -u > /tmp/epg_have.txt
python3 epg_channels.py --rank 1 --skip /tmp/epg_have.txt guides.json $G/heissa2.channels.xml m3u/de/all.m3u > /dev/null
(cd $G && npm run grab --silent -- --channels=heissa2.channels.xml --output=/tmp/epg2.xml --days=2 --maxConnections=4 > /tmp/epg_grab2.log 2>&1) || true
python3 epg_merge.py /tmp/epg1.xml /tmp/epg2.xml m3u/epg.xml.gz /var/lib/tvremote/epg_now.json
