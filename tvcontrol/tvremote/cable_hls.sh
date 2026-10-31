#!/bin/bash
# RTSP (FRITZ!Box cable) -> HLS in /dev/shm/cablehls/<n> for the browser player (cable.php);
# exits 30 s after the last playlist request.  usage: cable_hls.sh N RTSP_URL
n=$1 url=$2 D=/dev/shm/cablehls/$1
mkdir -p "$D" && cd "$D" || exit 1
rm -f ./*.ts index.m3u8
echo $$ > pid; touch last
# progressive H.264 (HD) is copied; interlaced SD or MPEG-2 is deinterlaced and encoded
probe=$(timeout 15 ffprobe -v error -rtsp_transport udp -timeout 8000000 -select_streams v:0 \
        -show_entries stream=codec_name,field_order -of csv=p=0 "$url")
case "$probe" in
    h264,progressive*) v=(-c:v copy) ;;
    *) v=(-vf yadif -c:v libx264 -preset veryfast -crf 23 -g 50) ;;
esac
ffmpeg -nostdin -loglevel error -rtsp_transport udp -timeout 10000000 -i "$url" \
    -map 0:v:0 -map 0:a:0 "${v[@]}" -c:a aac -b:a 128k -ac 2 \
    -f hls -hls_time 4 -hls_list_size 6 -hls_flags delete_segments+omit_endlist \
    -hls_segment_filename 'seg%d.ts' index.m3u8 &
ff=$!
trap 'kill $ff 2>/dev/null; wait $ff; rm -rf "$D"' EXIT
trap 'exit' TERM INT
while kill -0 $ff 2>/dev/null; do
    sleep 5
    [ $(( $(date +%s) - $(stat -c %Y last) )) -gt 30 ] && break
done
