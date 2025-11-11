import requests
from urllib.parse import urlparse
from pathlib import Path

# === CONFIG ===
DREW_PLAYLIST_URL = "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/MergedCleanPlaylist.m3u8"
CUSTOM_PLAYLIST_FILE = "playlist.m3u"
UPDATED_PLAYLIST_FILE = "playlist.m3u"

def parse_m3u(content):
    """Parses M3U content into a dictionary of {channel_name: url}."""
    lines = content.strip().splitlines()
    channels = {}
    for i in range(0, len(lines), 2):
        if lines[i].startswith("#EXTINF"):
            name_part = lines[i].split(",")[-1].strip()
            url_part = lines[i+1].strip()
            channels[name_part] = url_part
    return channels

def format_m3u(channels):
    """Formats a dictionary of {channel_name: url} into M3U content."""
    lines = ["#EXTM3U"]
    for name, url in channels.items():
        lines.append(f"#EXTINF:-1,{name}")
        lines.append(url)
    return "\n".join(lines)

def same_provider(url1, url2):
    """Returns True if both URLs share the same provider domain (e.g., moveonjoy.com)."""
    domain1 = urlparse(url1).netloc.lower()
    domain2 = urlparse(url2).netloc.lower()
    return domain1 == domain2

def main():
    # Load custom playlist
    if Path(CUSTOM_PLAYLIST_FILE).exists():
        with open(CUSTOM_PLAYLIST_FILE, "r", encoding="utf-8") as f:
            custom_channels = parse_m3u(f.read())
    else:
        print(f"{CUSTOM_PLAYLIST_FILE} not found.")
        return

    # Fetch DrewLive playlist
    r = requests.get(DREW_PLAYLIST_URL)
    r.raise_for_status()
    drew_channels = parse_m3u(r.text)

    # Update links only if provider matches
    for name, url in custom_channels.items():
        if name in drew_channels and same_provider(url, drew_channels[name]):
            custom_channels[name] = drew_channels[name]

    # Save updated playlist
    with open(UPDATED_PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(format_m3u(custom_channels))

    print(f"Playlist updated: {UPDATED_PLAYLIST_FILE}")

if __name__ == "__main__":
    main()
