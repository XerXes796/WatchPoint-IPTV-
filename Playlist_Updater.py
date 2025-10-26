#!/usr/bin/env python3
"""
Playlist_Updater.py

- MASTER_PLAYLIST_FILE : local "clean" playlist (the master)
- UPDATE_SOURCE_URL    : trusted source (raw url) to compare URLs against
Behavior:
  - For each channel in the master file (identified by the text after the last comma
    on the #EXTINF: line), if the update source contains the same channel and the URL
    differs, replace the URL in the master file.
  - Do NOT add channels that are not present in the master.
  - After saving, auto-stage/commit/pull-rebase/push, committing only if there are changes.
"""

import requests
import subprocess
import sys
from typing import List

# ========== CONFIG ==========
MASTER_PLAYLIST_FILE = "Watch-Point IPTV.m3u8"

# Replace this with the raw URL you trust for updates.
# Example:
# UPDATE_SOURCE_URL = "https://raw.githubusercontent.com/XerXes796/WatchPoint-IPTV-/main/Watch-Point%20IPTV.m3u8"
UPDATE_SOURCE_URL = "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/MergedCleanPlaylist.m3u8"

GIT_BRANCH = "main"
GIT_REMOTE = "origin"
GIT_COMMIT_MSG = "Auto-update IPTV URLs via Python script"
# ============================

def fetch_playlist_from_url(url: str) -> List[str]:
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.text.splitlines()

def load_local_playlist(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()

def save_local_playlist(path: str, lines: List[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Playlist saved to {path}")

def parse_master_to_channel_map(lines: List[str]) -> dict:
    """
    Returns mapping: channel_display_name -> (extinf_line_index)
    Channel display name is the part after the last comma on the #EXTINF: line.
    We'll use the display name as the match key because your master file uses that.
    """
    mapping = {}
    for i, line in enumerate(lines):
        if line.strip().startswith("#EXTINF"):
            parts = line.split(",")
            if parts:
                display = parts[-1].strip()
                mapping[display] = i
    return mapping

def build_update_dict(update_lines: List[str]) -> dict:
    """
    Returns mapping: channel_display_name -> url
    For channels found in the update source.
    """
    d = {}
    i = 0
    while i < len(update_lines):
        line = update_lines[i].strip()
        if line.startswith("#EXTINF"):
            parts = line.split(",")
            name = parts[-1].strip() if parts else ""
            url = update_lines[i+1].strip() if i+1 < len(update_lines) else ""
            if name:
                d[name] = url
            i += 2
        else:
            i += 1
    return d

def update_master_with_source(master_lines: List[str], update_map: dict) -> (List[str], int):
    """
    Walk master_lines and replace URL (the line after each #EXTINF) only if:
      - the channel display name exists in update_map
      - and the URL in update_map is different from the current master URL
    Returns (new_lines, number_of_updates)
    """
    new_lines = master_lines.copy()
    updates = 0
    i = 0
    while i < len(new_lines):
        line = new_lines[i]
        if line.strip().startswith("#EXTINF"):
            # display name = last comma part
            parts = line.split(",")
            display_name = parts[-1].strip() if parts else ""
            url_index = i + 1
            if url_index < len(new_lines):
                current_url = new_lines[url_index].strip()
                if display_name in update_map:
                    new_url = update_map[display_name].strip()
                    if new_url and new_url != current_url:
                        print(f"🔄 {display_name}: URL changed -> updating")
                        new_lines[url_index] = new_url
                        updates += 1
            i += 2
        else:
            i += 1
    return new_lines, updates

def run_git_commands_and_push(master_path: str, branch: str = GIT_BRANCH) -> None:
    """
    Stages the master file, commits only if there are changes, pulls (rebase) and pushes.
    Errors are printed and the function returns without raising so the script doesn't crash silently.
    """
    try:
        # set identity for automated commits (optional)
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)

        # Stage the file (all changes)
        subprocess.run(["git", "add", master_path], check=True)

        # If there are no staged changes, skip commit/pull/push
        diff_cached = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if diff_cached.returncode == 0:
            print("ℹ️ No changes to commit. Skipping git push.")
            return

        # Commit changes
        subprocess.run(["git", "commit", "-m", GIT_COMMIT_MSG], check=True)
        print("📦 Committed local changes.")

        # Pull remote changes first (use rebase to keep a linear history)
        try:
            subprocess.run(["git", "pull", "--rebase", GIT_REMOTE, branch], check=True)
            print("⬇️ Pulled remote changes (rebase).")
        except subprocess.CalledProcessError as e:
            # If rebase/pull fails, inform user and stop before pushing
            print("❌ Git pull --rebase failed. Resolve remote conflicts manually. Aborting push.")
            print(f"Git error: {e}")
            return

        # Push
        subprocess.run(["git", "push", GIT_REMOTE, branch], check=True)
        print("⬆️ Changes pushed to remote.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error while pushing: {e}")
        print("Please run git commands manually to inspect the repository state.")

def main():
    print("🔄 Loading master playlist...")
    try:
        master_lines = load_local_playlist(MASTER_PLAYLIST_FILE)
    except FileNotFoundError:
        print(f"❌ Master playlist file not found: {MASTER_PLAYLIST_FILE}")
        sys.exit(1)

    # Try fetch update source. If fails, we keep using master and do no changes.
    update_lines = None
    if UPDATE_SOURCE_URL and UPDATE_SOURCE_URL.strip():
        print(f"🔄 Fetching update source: {UPDATE_SOURCE_URL}")
        try:
            update_lines = fetch_playlist_from_url(UPDATE_SOURCE_URL)
        except Exception as e:
            print(f"⚠️ Could not fetch update playlist: {e}")
            print("No remote updates will be applied. Master will remain unchanged.")
            update_lines = None

    if not update_lines:
        print("ℹ️ No update source available, exiting without changes.")
        return

    # Build map from update source
    update_map = build_update_dict(update_lines)

    # Update master only when update_map has a same-named channel with a different URL
    new_master_lines, updates = update_master_with_source(master_lines, update_map)

    if updates == 0:
        print("ℹ️ No URLs changed. Nothing to write or push.")
        return

    # Save updated master
    save_local_playlist(MASTER_PLAYLIST_FILE, new_master_lines)

    # Auto commit & push safely
    run_git_commands_and_push(MASTER_PLAYLIST_FILE)

if __name__ == "__main__":
    main()
