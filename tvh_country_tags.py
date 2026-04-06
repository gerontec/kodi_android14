#!/usr/bin/env python3
"""Assign country tags to TVHeadend channels via API."""
import json, re, requests
from requests.auth import HTTPDigestAuth

TVH = "http://192.168.178.218:9981"
AUTH = HTTPDigestAuth("admin", "654321")

def api(path, data=None):
    if data:
        r = requests.post(f"{TVH}{path}", auth=AUTH, data=data)
    else:
        r = requests.get(f"{TVH}{path}", auth=AUTH)
    try:
        return r.json()
    except Exception:
        return {"status": r.status_code, "text": r.text[:100]}

# 1. Get all channels (uuid -> name)
print("Fetching channels...")
chs = api("/api/channel/grid?limit=2000&all=1")["entries"]
# Build Kodi-index -> uuid map (by position, same order as PVR.GetChannels)
# Use name to match instead - parse channels_by_country.md by name
name2uuid = {c["name"]: c["uuid"] for c in chs}
uuid2tags = {c["uuid"]: c.get("tags", []) for c in chs}
print(f"  {len(chs)} channels loaded")

# 2. Parse channels_by_country.md
print("Parsing country mapping...")
mapping = {}  # channel_name_partial -> (flag, country_en, country_native)
country = None
with open("/tmp/channels_by_country.md") as f:
    for line in f:
        line = line.strip()
        m = re.match(r'^## (.+?) / (.+)', line)
        if m:
            left = m.group(1).strip()
            right = m.group(2).strip()
            parts = left.split(' ', 1)
            flag = parts[0]
            country_en = parts[1] if len(parts) > 1 else left
            country_native = right
            country = (flag, country_en, country_native)
            continue
        m2 = re.match(r'^- \d+ \| (.+?) \| (.+)', line)
        if m2 and country:
            ch_name = m2.group(1).strip()
            mapping[ch_name] = country
print(f"  {len(mapping)} channels in mapping")

# 3. Get existing tags
print("Fetching existing tags...")
existing_tags = api("/api/idnode/load?uuid=tag&class=channeltag&limit=200")
# Build name -> uuid for tags
tag_name2uuid = {}
if "entries" in existing_tags:
    for t in existing_tags["entries"]:
        tag_name2uuid[t.get("val", "")] = t.get("key", "")
print(f"  {len(tag_name2uuid)} existing tags")

# 4. Create missing country tags
print("Creating country tags...")
countries = {}
for ch_name, (flag, en, native) in mapping.items():
    tag_name = f"{flag} {en}" if en == native else f"{flag} {en} / {native}"
    countries[tag_name] = (flag, en, native)

created = 0
for tag_name in sorted(countries.keys()):
    if tag_name not in tag_name2uuid:
        resp = api("/api/channeltag/create", {"conf": json.dumps({"name": tag_name, "enabled": True})})
        if "uuid" in resp:
            tag_name2uuid[tag_name] = resp["uuid"]
            created += 1
print(f"  Created {created} new tags")

# 5. Assign tags to channels
print("Assigning country tags to channels...")
updated = 0
skipped = 0
for ch_name, (flag, en, native) in mapping.items():
    tag_label = f"{flag} {en}" if en == native else f"{flag} {en} / {native}"
    tag_uuid = tag_name2uuid.get(tag_label)
    if not tag_uuid:
        skipped += 1
        continue
    # Find channel uuid by name
    ch_uuid = name2uuid.get(ch_name)
    if not ch_uuid:
        # Try partial match (strip resolution suffix like " (1080p)")
        base = re.sub(r'\s*\(\d+p\).*$', '', ch_name).strip()
        for n, u in name2uuid.items():
            if re.sub(r'\s*\(\d+p\).*$', '', n).strip() == base:
                ch_uuid = u
                break
    if not ch_uuid:
        skipped += 1
        continue
    current_tags = uuid2tags.get(ch_uuid, [])
    if tag_uuid not in current_tags:
        new_tags = current_tags + [tag_uuid]
        resp = api("/api/channel/save", {
            "uuid": ch_uuid,
            "conf": json.dumps({"tags": new_tags})
        })
        updated += 1

print(f"  Updated: {updated}, Skipped: {skipped}")
print("Done!")
