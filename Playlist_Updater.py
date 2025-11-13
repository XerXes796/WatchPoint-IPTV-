import requests
import re
import gzip
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from typing import Dict, List, Tuple, Optional, Set
from io import BytesIO

# Your local playlist file
PLAYLIST_FILE = "playlist.m3u"

# Your local EPG file
EPG_FILE = "watchpoint-iptv-playlist.xml.gz"

# DrewLive playlist URL
DREW_PLAYLIST_URL = "http://drewlive24.duckdns.org:8081/DrewLive/MergedCleanPlaylist.m3u8"

# DrewLive EPG URL (adjust if different)
DREW_EPG_URL = "https://raw.githubusercontent.com/DrewLiveTemp/DrewskiTemp24/main/DrewLive.xml.gz"

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
    """Parse M3U playlist into list of channel dictionaries (supports extra option lines)"""
    channels: List[Dict] = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line or line == "#EXTM3U":
            i += 1
            continue

        if line.startswith("#EXTINF"):
            tvg_id_match = re.search(r'tvg-id="([^"]+)"', line)
            tvg_id = tvg_id_match.group(1) if tvg_id_match else None

            name_match = re.search(r',(.+)$', line)
            channel_name = name_match.group(1).strip() if name_match else ""

            j = i + 1
            extras: List[str] = []
            url: Optional[str] = None

            while j < len(lines):
                candidate = lines[j].strip()

                if candidate.startswith("#EXTINF"):
                    break

                if candidate.startswith("http://") or candidate.startswith("https://"):
                    url = candidate
                    j += 1
                    break

                extras.append(lines[j])
                j += 1

            if url:
                provider = extract_provider_domain(url)
                channels.append({
                    "extinf": line,
                    "url": url,
                    "extras": extras,
                    "tvg_id": tvg_id,
                    "name": channel_name,
                    "provider": provider,
                    "original_index": len(channels),
                })
            else:
                print(f"⚠️  Skipping channel (no playable URL found): {channel_name or '[unknown]'}")

            i = j
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

    for local_ch in local_channels:
        drew_ch = find_matching_channel(local_ch, drew_channels)

        if drew_ch and should_update_channel(local_ch, drew_ch):
            output_lines.append(drew_ch["extinf"])
            for extra in (local_ch.get("extras") or drew_ch.get("extras") or []):
                output_lines.append(extra)
            output_lines.append(drew_ch["url"])
            updated_count += 1
            print(f"✅ Updated: {local_ch['name']} ({local_ch['provider']})")
            print(f"   Old: {local_ch['url']}")
            print(f"   New: {drew_ch['url']}")
        else:
            output_lines.append(local_ch["extinf"])
            for extra in local_ch.get("extras", []):
                output_lines.append(extra)
            output_lines.append(local_ch["url"])

            if drew_ch:
                if local_ch["provider"] != drew_ch["provider"]:
                    print(f"⚠️  Skipped: {local_ch['name']} - Provider mismatch")
                    print(f"   Local: {local_ch['provider']} | DrewLive: {drew_ch['provider']}")
            # No log when the URL is unchanged or the channel is missing upstream

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

def get_local_channel_ids(local_channels: List[Dict]) -> Set[str]:
    """Extract set of tvg-ids from local playlist channels"""
    channel_ids = set()
    for ch in local_channels:
        if ch['tvg_id']:
            channel_ids.add(ch['tvg_id'])
    return channel_ids

def fetch_drew_epg() -> Optional[bytes]:
    """Fetch DrewLive EPG from GitHub"""
    try:
        response = requests.get(DREW_EPG_URL, timeout=30, stream=True)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"⚠️  Error fetching DrewLive EPG: {e}")
        return None

def parse_xmltv_epg(epg_data: bytes) -> Tuple[ET.Element, Dict[str, ET.Element]]:
    """Parse XMLTV EPG data and return root element and channel dictionary"""
    try:
        # Decompress if gzipped
        try:
            decompressed = gzip.decompress(epg_data)
        except:
            decompressed = epg_data
        
        # Parse XML
        root = ET.fromstring(decompressed)
        
        # Build channel dictionary: channel_id -> channel_element
        channels_dict = {}
        for channel in root.findall('.//channel'):
            channel_id = channel.get('id')
            if channel_id:
                channels_dict[channel_id] = channel
        
        return root, channels_dict
    except Exception as e:
        print(f"❌ Error parsing EPG XML: {e}")
        raise

def filter_epg_by_channels(epg_root: ET.Element, channel_ids: Set[str], channels_dict: Dict[str, ET.Element]) -> ET.Element:
    """Filter EPG to only include channels that exist in local playlist"""
    # Create new root element
    new_root = ET.Element('tv')
    
    # Copy attributes from original root
    for key, value in epg_root.attrib.items():
        new_root.set(key, value)
    
    # Filter channels - only keep channels with matching tvg-ids
    kept_channel_ids = set()
    for channel_id in channel_ids:
        if channel_id in channels_dict:
            new_root.append(channels_dict[channel_id])
            kept_channel_ids.add(channel_id)
            print(f"📺 Keeping EPG for: {channel_id}")
    
    # Filter programmes - only keep programmes for channels we kept
    for programme in epg_root.findall('.//programme'):
        channel_ref = programme.get('channel')
        if channel_ref in kept_channel_ids:
            new_root.append(programme)
    
    print(f"✅ Filtered EPG: {len(kept_channel_ids)} channels, {len(new_root.findall('.//programme'))} programmes")
    return new_root

def save_epg(epg_root: ET.Element):
    """Save filtered EPG to compressed XML file"""
    try:
        # Convert XML tree to string
        xml_string = ET.tostring(epg_root, encoding='utf-8', xml_declaration=True)
        
        # Compress and save
        with gzip.open(EPG_FILE, 'wb') as f:
            f.write(xml_string)
        
        print(f"✅ EPG saved to {EPG_FILE}")
    except Exception as e:
        print(f"❌ Error saving EPG: {e}")
        raise

def update_epg(local_channels: List[Dict]) -> bool:
    """Update EPG file by filtering DrewLive EPG to match local playlist channels"""
    print("\n📥 Fetching DrewLive EPG...")
    epg_data = fetch_drew_epg()
    
    if not epg_data:
        print("⚠️  Could not fetch DrewLive EPG. Skipping EPG update.")
        return False
    
    print("📺 Parsing EPG data...")
    epg_root, channels_dict = parse_xmltv_epg(epg_data)
    
    print(f"📊 Found {len(channels_dict)} channels in DrewLive EPG")
    
    # Get channel IDs from local playlist
    local_channel_ids = get_local_channel_ids(local_channels)
    print(f"📊 Local playlist has {len(local_channel_ids)} channels with tvg-id")
    
    # Filter EPG to only include local channels
    print("\n🔄 Filtering EPG to match local playlist...")
    filtered_epg = filter_epg_by_channels(epg_root, local_channel_ids, channels_dict)
    
    # Save filtered EPG
    print("\n💾 Saving filtered EPG...")
    save_epg(filtered_epg)
    
    return True

def main():
    # Update playlist
    print("=" * 60)
    print("📺 PLAYLIST UPDATE")
    print("=" * 60)
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
        print("\n✅ No playlist updates needed - all channels are up to date!")
        # Still save to ensure file format is consistent
        save_playlist(updated_lines)
    
    # Update EPG
    print("\n" + "=" * 60)
    print("📺 EPG UPDATE")
    print("=" * 60)
    epg_updated = update_epg(local_channels)
    
    if epg_updated:
        print("\n✅ EPG update completed successfully!")
    else:
        print("\n⚠️  EPG update skipped or failed.")
    
    print("\n" + "=" * 60)
    print("✅ ALL UPDATES COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error updating playlist/EPG: {e}")
        import traceback
        traceback.print_exc()
        exit(1)