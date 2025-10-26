import requests

MASTER_PLAYLIST = "Watch-Point IPTV.m3u8"
UPDATE_SOURCE_URL = "http://drewlive24.duckdns.org/your_source.m3u8"

def fetch_playlist(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.text.splitlines()

def build_update_dict(source_lines):
    """
    Builds a dictionary of channel_name -> updated_url
    from the source playlist. Only includes channels that exist in the source.
    """
    update_dict = {}
    for i in range(len(source_lines)):
        line = source_lines[i]
        if line.startswith("#EXTINF"):
            channel_name = line.split(",")[-1].strip()
            if i + 1 < len(source_lines):
                url = source_lines[i + 1].strip()
                update_dict[channel_name] = url
    return update_dict

def update_master_playlist(master_file, update_dict):
    """
    Updates URLs in master playlist only if a new URL exists for that channel.
    Does NOT add or remove channels, and ignores unrelated URLs.
    """
    with open(master_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        updated_lines.append(line)

        if line.startswith("#EXTINF"):
            channel_name = line.strip().split(",")[-1]
            if i + 1 < len(lines):
                current_url = lines[i + 1].strip()
                # Only replace if channel exists in update_dict and URL is different
                if channel_name in update_dict and current_url != update_dict[channel_name]:
                    updated_lines.append(update_dict[channel_name] + "\n")
                else:
                    updated_lines.append(lines[i + 1])
                i += 1  # Skip old URL
        i += 1

    with open(master_file, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

if __name__ == "__main__":
    print("🔄 Fetching updated playlist...")
    source_lines = fetch_playlist(UPDATE_SOURCE_URL)
    updates = build_update_dict(source_lines)
    print("🔄 Updating master playlist URLs...")
    update_master_playlist(MASTER_PLAYLIST, updates)
    print(f"✅ Playlist updated and saved to {MASTER_PLAYLIST}")
