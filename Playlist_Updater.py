import requests
import subprocess
from datetime import datetime
from urllib.parse import urlparse

# =========================
# CONFIGURATION
# =========================
MASTER_FILE = "Watch-Point IPTV.m3u8"
UPDATE_SOURCE_URL = "https://raw.githubusercontent.com/XerXes796/WatchPoint-IPTV-/refs/heads/main/Watch-point%20IPTV.m3u8"

# =========================
# FETCHING FUNCTIONS
# =========================
def fetch_playlist(url):
    print(f"🔄 Fetching playlist from {url}")
    r = requests.get(url)
    r.raise_for_status()
    return [line.strip() for line in r.text.splitlines() if line.strip()]

def extract_tvg_id(line):
    if 'tvg-id="' in line:
        start = line.find('tvg-id="') + 8
        end = line.find('"', start)
        return line[start:end].strip()
    return None

# =========================
# DOMAIN CHECK HELPERS
# =========================
def get_domain(url):
    """Return the domain (without www) from a URL."""
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return None

def same_source(url1, url2):
    """Check if two URLs are from the same media source/domain."""
    if not url1 or not url2:
        return False
    d1, d2 = get_domain(url1), get_domain(url2)
    if not d1 or not d2:
        return False
    return d1.split('.')[-2:] == d2.split('.')[-2:]  # match base domain

# =========================
# UPDATE LOGIC
# =========================
def update_playlist(master_lines, source_lines):
    updated_lines = []
    i = 0
    while i < len(master_lines):
        line = master_lines[i]
        if line.startswith("#EXTINF"):
            url = master_lines[i + 1] if i + 1 < len(master_lines) else ""
            channel_id = extract_tvg_id(line)
            if not channel_id:
                updated_lines.extend([line, url])
                i += 2
                continue

            for j in range(0, len(source_lines), 2):
                if j + 1 >= len(source_lines):
                    continue
                src_info, src_url = source_lines[j], source_lines[j + 1]
                if channel_id == extract_tvg_id(src_info):
                    if same_source(url, src_url):
                        url = src_url
                    break

            updated_lines.extend([line, url])
            i += 2
        else:
            updated_lines.append(line)
            i += 1
    return updated_lines

# =========================
# GIT FUNCTIONS
# =========================
def git_push():
    try:
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
        subprocess.run(["git", "add", MASTER_FILE], check=True)
        commit_message = f"Auto-update IPTV URLs via Python script - {datetime.now():%Y-%m-%d %H:%M:%S}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ Successfully pushed updated playlist to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")

# =========================
# MAIN EXECUTION
# =========================
if __name__ == "__main__":
    try:
        source_lines = fetch_playlist(UPDATE_SOURCE_URL)
    except Exception as e:
        print(f"⚠️ Could not fetch update playlist: {e}\nUsing master playlist only.")
        source_lines = []

    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        master_lines = [line.strip() for line in f.readlines() if line.strip()]

    updated_lines = update_playlist(master_lines, source_lines if source_lines else master_lines)

    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(updated_lines))

    print(f"✅ Playlist saved to {MASTER_FILE}")

    # Auto-push changes to GitHub
    git_push()
