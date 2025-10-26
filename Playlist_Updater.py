import requests
import re
import subprocess
import sys

# --- Configuration ---
PLAYLIST_URL = "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/MergedCleanPlaylist.m3u8"
OUTPUT_FILE = "Watch-Point IPTV.m3u8"

# Allowed groups (you can customize)
ALLOWED_GROUPS = [
    "A1xmedia CA Sports",
    "A1xmedia US Sports",
    "MoveOnJoy",
    "PlexTV",
    "TubiTV"
]

# --- Fetch Drew's playlist ---
def fetch_playlist(url):
    try:
        r = requests.get(url)
        r.raise_for_status()
        return r.text.splitlines()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch playlist: {e}")
        sys.exit(1)

# --- Process each EXTINF line ---
def remap_group_title(line):
    if line.startswith("#EXTINF:"):
        match = re.search(r'group-title="([^"]*)"', line)
        original_group = match.group(1) if match else "Unknown"
        if original_group not in ALLOWED_GROUPS:
            return None
        # Keep original group-title
        line = re.sub(r'\s*group-title="[^"]*"', '', line)
        parts = line.split(",", 1)
        header = parts[0].strip()
        title = parts[1] if len(parts) > 1 else ""
        header += f' group-title="{original_group}"'
        return f"{header},{title}"
    return line

# --- Generate final playlist ---
def process_playlist(lines):
    output_lines = ["#EXTM3U"]
    keep_channel = False
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            new_line = remap_group_title(line)
            if new_line:
                output_lines.append(new_line)
                keep_channel = True
            else:
                keep_channel = False
        elif line.startswith("http") and keep_channel:
            output_lines.append(line)
    return output_lines

# --- Save playlist to file ---
def save_playlist(lines):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Playlist updated and saved to {OUTPUT_FILE}")

# --- Git auto-push ---
def git_push():
    try:
        subprocess.run(["git", "add", OUTPUT_FILE], check=True)
        # Only commit if changes exist
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], check=False
        )
        if result.returncode != 0:
            subprocess.run(["git", "commit", "-m", "Auto-update playlist via Python script"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("✅ Playlist changes pushed to GitHub")
        else:
            print("ℹ️ No changes to push")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")

# --- Main ---
if __name__ == "__main__":
    lines = fetch_playlist(PLAYLIST_URL)
    final_output = process_playlist(lines)
    save_playlist(final_output)
    git_push()
