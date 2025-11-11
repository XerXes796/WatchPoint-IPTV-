import requests
import re
from urllib.parse import urlparse
from typing import Dict, List, Tuple, Optional

# Your local playlist file
PLAYLIST_FILE = "playlist.m3u"

# DrewLive playlist URL
DREW_PLAYLIST_URL = "https://raw.githubusercontent.com/Drewski2423/DrewLive/refs/heads/main/MergedCleanPlaylist.m3u8"

def extract_provider_domain(url: str) -> str:
    """Extract the main provider domain from a URL"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        # Remove port if present
        hostname = hostname.split(':')[0]
        
        # For IP addresses, return as-is
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
            return hostname
        
        # Extract base domain (e.g., 'moveonjoy.com' from 'fl1.moveonjoy.com')
        # or 'portal5458.com' from 'portal5458.com'
        parts = hostname.split('.')
        if len(parts) >= 2:
            # Get last two parts for most domains (e.g., moveonjoy.com, portal5458.com)
            return '.'.join(parts[-2:])
        return hostname
    except:
        return ""

def parse_m3u_playlist(lines: List[str]) -> List[Dict]:
    """Parse M3U playlist into list of channel dictionaries"""
    channels = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines and header
        if not line or line == "#EXTM3U":
            i += 1
            continue
        
        # Check if this is an #EXTINF line
        if line.startswith("#EXTINF"):
            # Extract tvg-id if present
            tvg_id_match = re.search(r'tvg-id="([^"]+)"', line)
            tvg_id = tvg_id_match.group(1) if tvg_id_match else None
            
            # Extract channel name (after the last comma)
            name_match = re.search(r',(.+)$', line)
            channel_name = name_match.group(1).strip() if name_match else ""
            
            # Get URL from next line
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and (url.startswith("http://") or url.startswith("https://")):
                    provider = extract_provider_domain(url)
                    channels.append({
                        'extinf': line,
                        'url': url,
                        'tvg_id': tvg_id,
                        'name': channel_name,
                        'provider': provider,
                        'original_index': len(channels)
                    })
                    i += 2  # Skip both EXTINF and URL lines
                    continue
        
        i += 1
    
    return channels

def find_matching_channel(local_channel: Dict, drew_channels: List[Dict]) -> Optional[Dict]:
    """Find matching channel in DrewLive playlist by tvg-id or name"""
    # First try to match by tvg-id (most reliable)
    if local_channel['tvg_id']:
        for drew_ch in drew_channels:
            if drew_ch['tvg_id'] == local_channel['tvg_id']:
                return drew_ch
    
    # Fallback to channel name matching (exact match, case-insensitive)
    if local_channel['name']:
        local_name = local_channel['name'].strip().lower()
        for drew_ch in drew_channels:
            drew_name = drew_ch['name'].strip().lower()
            if drew_name == local_name:
                return drew_ch
    
    return None

def should_update_channel(local_channel: Dict, drew_channel: Dict) -> bool:
    """Determine if channel should be updated - MUST be same provider AND same channel"""
    # CRITICAL: Only update if provider domain matches exactly
    if local_channel['provider'] != drew_channel['provider']:
        return False
    
    # Only update if URL actually changed
    if local_channel['url'] == drew_channel['url']:
        return False
    
    return True

def update_playlist(local_channels: List[Dict], drew_channels: List[Dict]) -> Tuple[List[str], int]:
    """Update local playlist with changes from DrewLive, preserving order and NEVER adding new channels"""
    updated_count = 0
    output_lines = ["#EXTM3U"]
    
    # IMPORTANT: Only iterate through local_channels - this ensures NO new channels are added
    for local_ch in local_channels:
        # Try to find matching channel in DrewLive
        drew_ch = find_matching_channel(local_ch, drew_channels)
        
        if drew_ch and should_update_channel(local_ch, drew_ch):
            # Update this channel (same provider, same channel, URL changed)
            output_lines.append(drew_ch['extinf'])
            output_lines.append(drew_ch['url'])
            updated_count += 1
            print(f"✅ Updated: {local_ch['name']} ({local_ch['provider']})")
            print(f"   Old: {local_ch['url']}")
            print(f"   New: {drew_ch['url']}")
        else:
            # Keep original channel unchanged
            output_lines.append(local_ch['extinf'])
            output_lines.append(local_ch['url'])
            
            # Log why it wasn't updated (for debugging)
            if drew_ch:
                if local_ch['provider'] != drew_ch['provider']:
                    print(f"⚠️  Skipped: {local_ch['name']} - Provider mismatch")
                    print(f"   Local: {local_ch['provider']} | DrewLive: {drew_ch['provider']}")
                elif local_ch['url'] == drew_ch['url']:
                    # Same URL, no update needed (silent)
                    pass
            else:
                # Channel not found in DrewLive - keep original (silent)
                pass
    
    return output_lines, updated_count

def fetch_drew_playlist():
    """Fetch DrewLive playlist from GitHub"""
    response = requests.get(DREW_PLAYLIST_URL, timeout=15)
    response.raise_for_status()
    return response.text.splitlines()

def load_local_playlist():
    """Load local playlist file"""
    with open(PLAYLIST_FILE, "r", encoding="utf-8") as f:
        return f.read().splitlines()

def save_playlist(lines: List[str]):
    """Save playlist to file"""
    if not lines or len(lines) <= 1:  # Only header
        print("⚠️ Playlist is empty! Skipping overwrite.")
        return
    
    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"✅ Playlist saved. {len(lines)} lines written.")

def main():
    print("📥 Fetching DrewLive playlist...")
    drew_lines = fetch_drew_playlist()
    drew_channels = parse_m3u_playlist(drew_lines)
    print(f"📺 Found {len(drew_channels)} channels in DrewLive playlist")
    
    print("📥 Loading local playlist...")
    local_lines = load_local_playlist()
    local_channels = parse_m3u_playlist(local_lines)
    print(f"📺 Found {len(local_channels)} channels in local playlist")
    
    print("\n🔄 Checking for updates (ALL providers)...")
    print("   Rules: Same provider + Same channel + URL changed = Update")
    print("   Rules: Different provider = Keep original")
    print("   Rules: Channel not in DrewLive = Keep original")
    print("   Rules: NO new channels will be added\n")
    
    updated_lines, updated_count = update_playlist(local_channels, drew_channels)
    
    if updated_count > 0:
        print(f"\n✨ Updated {updated_count} channel(s)")
        save_playlist(updated_lines)
    else:
        print("\n✅ No updates needed - all channels are up to date!")
        # Still save to ensure file format is consistent
        save_playlist(updated_lines)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error updating playlist: {e}")
        import traceback
        traceback.print_exc()
        exit(1)