import sqlite3
import os

# === Engine DJ SQLite DB path ===
# TODO: Set your Engine DJ database file here:
ENGINE_DB_PATH = r"YOUR_ENGINE_DB_PATH_HERE"

# === Path to M3U playlist ===
# TODO: Set your input M3U file here:
PLAYLIST_FILE = "YOUR_PLAYLIST_FILE.m3u"

print(f"🔍 Using Engine DJ database: {ENGINE_DB_PATH}")

# === 1️⃣ Parse M3U playlist ===
tracks = []
current_rating = None

with open(PLAYLIST_FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

for line in lines:
    line = line.strip()
    if not line:
        continue

    if line.startswith("#EXT-X-RATING:"):
        current_rating = int(line.split(":")[1])
        continue

    if line.startswith("#"):
        continue

    # Normalize to URI format
    location = line.replace("\\", "/")
    if not location.startswith("file://localhost/"):
        location = "file://localhost/" + location

    tracks.append({
        "location": location,
        "rating": current_rating if current_rating else 0
    })

print(f"✅ Playlist parsed → Tracks: {len(tracks)}")

# === 2️⃣ Connect to Engine DJ database ===
conn = sqlite3.connect(ENGINE_DB_PATH)
cursor = conn.cursor()

log = []
updated = 0
not_found = 0

for track in tracks:
    location = track["location"]
    raw = track["rating"]

    # Normalize M3U 1–5 stars to Engine DJ scale (1–5 * 20)
    if raw <= 5:
        rating = raw * 20
    else:
        rating = raw

    print(f"\n➡️  Updating: {location} → M3U={raw} → Final={rating}")

    # Convert absolute URI to relative DB path (Engine DJ style)
    if location.startswith("file://localhost/"):
        abs_path = location.replace("file://localhost/", "").replace("\\", "/")
        if ":/" in abs_path:
            rel_path = "../" + abs_path.split(":/", 1)[1]
        else:
            rel_path = abs_path
    else:
        rel_path = location

    print(f"🔍 DB lookup path: {rel_path}")

    cursor.execute("SELECT id, path, rating FROM Track WHERE path = ?", (rel_path,))
    row = cursor.fetchone()

    if row:
        track_id, old_path, old_rating = row

        print(f"✅ FOUND → id={track_id} | Old Rating={old_rating}")

        if old_rating != rating:
            cursor.execute("UPDATE Track SET rating = ? WHERE id = ?", (rating, track_id))
            log.append(f"UPDATED: id={track_id} → {old_path} → {old_rating} → {rating}")
            updated += 1
        else:
            log.append(f"SKIPPED: id={track_id} → {old_path} → Same Rating ({rating})")

    else:
        print(f"❌ NOT FOUND: {rel_path}")
        log.append(f"NOT FOUND: {rel_path}")
        not_found += 1

# === 3️⃣ Commit and close DB ===
conn.commit()
conn.close()

print(f"\n✅ DONE: Updated={updated} | Not Found={not_found}")

# === 4️⃣ Write update log ===
with open("update_enginedj_log.txt", "w", encoding="utf-8") as f:
    for entry in log:
        f.write(entry + "\n")

print("📂 Log saved to update_enginedj_log.txt")
