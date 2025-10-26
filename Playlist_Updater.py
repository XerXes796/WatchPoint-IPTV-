import requests
import re

# Your playlist (custom order)
MY_PLAYLIST = "Watch-point IPTV.m3u8"
# Drew's raw playlist
DREW_PLAYLIST_URL = "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/MergedCleanPlaylist.m3u8"

def fetch_playlist(url):
    """Fetch and return playlist lines from a URL"""
    r = requests.get(url)
    r.raise_for_status()
    return r.text.splitlines()

def build_url_map(lines):
    """
    Build a dictionary mapping tvg-id -> URL from Drew's playlist
    """
    url_map = {}
    current_id = None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            match = re.search(r'tvg-id="([^"]+)"', line)
            current_id = match.group(1) if match else None
        elif line.startswith("http") and current_id:
            url_map[current_id] = line
            current_id = None
    return url_map

def update_my_playlist(my_lines, drew_map):
    """
    Update URLs in your playlist based on Drew's mapping
    """
    output_lines = []
    keep_next_url = False
    current_id = None

    for line in my_lines:
        line = line.rstrip("\n")
        if line.startswith("#EXTINF:"):
            match = re.search(r'tvg-id="([^"]+)"', line)
            current_id = match.group(1) if match else None
            output_lines.append(line)
            keep_next_url = current_id in drew_map
        elif line.startswith("http") and keep_next_url and current_id in drew_map:
            output_lines.append(drew_map[current_id])
            keep_next_url = False
        else:
            output_lines.append(line)
            keep_next_url = False

    return output_lines

if __name__ == "__main__":
    # Fetch Drew's playlist
    drew_lines = fetch_playlist(DREW_PLAYLIST_URL)
    drew_map = build_url_map(drew_lines)

    # Read your current playlist
    with open(MY_PLAYLIST, "r", encoding="utf-8") as f:
        my_lines = f.readlines()

    # Update playlist URLs
    updated_lines = update_my_playlist(my_lines, drew_map)

    # Save back to your playlist
    with open(MY_PLAYLIST, "w", encoding="utf-8") as f:
        f.write("\n".join(updated_lines))

    print(f"✅ Playlist updated and saved to {MY_PLAYLIST}")
