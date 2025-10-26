import requests

# === CONFIGURATION ===
MASTER_PLAYLIST_FILE = "Watch-Point IPTV.m3u8"  # your clean master playlist
UPDATE_SOURCE_URL = "https://raw.githubusercontent.com/YourGitHubUser/YourRepo/main/Watch-Point IPTV.m3u8"
# If you don't want online updates, you can comment out UPDATE_SOURCE_URL and keep everything local.

def fetch_playlist(url):
    """Fetch playlist lines from a URL."""
    r = requests.get(url)
    r.raise_for_status()
    return r.text.splitlines()

def load_local_playlist(file_path):
    """Load playlist lines from local file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().splitlines()

def save_playlist(file_path, lines):
    """Save playlist lines to file."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Playlist saved to {file_path}")

def parse_channels(lines):
    """Return a dict mapping channel name -> URL"""
    channels = {}
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            # channel name is after the last comma
            channel_name = line.split(",")[-1].strip()
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                channels[channel_name] = url
    return channels

def update_playlist(master_lines, update_lines):
    """Update master playlist URLs only if changed in the update source"""
    update_channels = parse_channels(update_lines)
    new_lines = master_lines.copy()
    i = 0
    while i < len(new_lines):
        line = new_lines[i]
        if line.startswith("#EXTINF"):
            channel_name = line.split(",")[-1].strip()
            if channel_name in update_channels:
                old_url = new_lines[i + 1].strip()
                new_url = update_channels[channel_name]
                if old_url != new_url:
                    print(f"🔄 Updating URL for {channel_name}")
                    new_lines[i + 1] = new_url
            i += 2  # skip URL line
        else:
            i += 1
    return new_lines

def main():
    try:
        master_lines = load_local_playlist(MASTER_PLAYLIST_FILE)
    except FileNotFoundError:
        print(f"❌ Master playlist {MASTER_PLAYLIST_FILE} not found!")
        return

    try:
        update_lines = fetch_playlist(UPDATE_SOURCE_URL)
    except Exception as e:
        print(f"⚠️ Could not fetch update playlist: {e}")
        print("Using master playlist only.")
        update_lines = master_lines  # fallback: no changes

    updated_lines = update_playlist(master_lines, update_lines)
    save_playlist(MASTER_PLAYLIST_FILE, updated_lines)

if __name__ == "__main__":
    main()
