import requests
import re
import subprocess

MY_PLAYLIST = "Watch-Point IPTV.m3u8"
DREW_PLAYLIST = "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/MergedCleanPlaylist.m3u8"

def fetch_playlist(url_or_file):
    """Fetch playlist from a URL or read from local file"""
    if url_or_file.startswith("http"):
        r = requests.get(url_or_file)
        r.raise_for_status()
        return r.text.splitlines()
    else:
        with open(url_or_file, "r", encoding="utf-8") as f:
            return f.read().splitlines()

def build_drew_dict(drew_lines):
    """Create a mapping from tvg-id to URL from Drew's playlist"""
    drew_map = {}
    i = 0
    while i < len(drew_lines):
        line = drew_lines[i].strip()
        if line.startswith("#EXTINF:"):
            match = re.search(r'tvg-id="([^"]+)"', line)
            if match and (i + 1) < len(drew_lines):
                tvg_id = match.group(1)
                url = drew_lines[i + 1].strip()
                drew_map[tvg_id] = url
            i += 2
        else:
            i += 1
    return drew_map

def update_playlist(my_lines, drew_map):
    """Update only the URLs for channels that exist in the original playlist"""
    updated_lines = []
    i = 0
    while i < len(my_lines):
        line = my_lines[i].strip()
        if line.startswith("#EXTINF:"):
            updated_lines.append(line)
            match = re.search(r'tvg-id="([^"]+)"', line)
            if match:
                tvg_id = match.group(1)
                if (i + 1) < len(my_lines):
                    original_url = my_lines[i + 1].strip()
                    # Only replace URL if Drew has an update for this tvg-id
                    new_url = drew_map.get(tvg_id, original_url)
                    updated_lines.append(new_url)
            i += 2
        else:
            updated_lines.append(line)
            i += 1
    return updated_lines

def push_changes():
    try:
        subprocess.run(["git", "add", MY_PLAYLIST], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-update IPTV URLs via Python script"], check=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ Playlist pushed to GitHub!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")

if __name__ == "__main__":
    print("🔄 Fetching playlists...")
    my_lines = fetch_playlist(MY_PLAYLIST)
    drew_lines = fetch_playlist(DREW_PLAYLIST)

    print("🔄 Updating URLs only for existing channels...")
    drew_map = build_drew_dict(drew_lines)
    updated_lines = update_playlist(my_lines, drew_map)

    with open(MY_PLAYLIST, "w", encoding="utf-8") as f:
        f.write("\n".join(updated_lines))
    print(f"✅ Playlist updated and saved to {MY_PLAYLIST}")

    # Push to GitHub
    push_changes()
