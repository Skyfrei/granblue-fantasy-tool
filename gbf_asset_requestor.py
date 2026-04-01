import requests
import os

CDN_BASE = "https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/assets"

CDN_PATH_MAP = {
    "char": "npc/s",
    "summon": "summon/b",
    "raid": "quest/l",
    "leader": "leader/pm" # MC Classes/Skins
}

def get_wiki_image_by_id(asset_id, asset_type="char"):
    api_url = "https://gbf.wiki/api.php"
    headers = {'User-Agent': 'GBF-Asset-Downloader/1.1'}
    prefix_map = {"char": "Npc_s_", "summon": "Summon_m_", "raid": "Quest_l_"}
    prefix = prefix_map.get(asset_type, "")

    params = {
        "action": "query", "format": "json", "list": "allimages",
        "aifrom": f"{prefix}{asset_id}", "ailimit": 1
    }
    
    try:
        response = requests.get(api_url, params=params, headers=headers)
        data = response.json()
        images = data.get('query', {}).get('allimages', [])
        if not images: return None
        filename = images[0]['name']
        if str(asset_id) not in filename: return None
        return f"https://gbf.wiki/Special:FilePath/{filename}"
    except:
        return None

def get_official_cdn_url(asset_id, asset_type):
    """Constructs the official game link with MC/Leader redirection."""
    id_str = str(asset_id)
    
    # Redirect MC/Classes (1xxxx) or Skins (4xxxx) to the leader folder
    if asset_type == "char" and (id_str.startswith("4") or id_str.startswith("1")):
        path = CDN_PATH_MAP["leader"]
    else:
        path = CDN_PATH_MAP.get(asset_type, "npc/s")

    ext = "jpg" if asset_type == "raid" else "png"
    # Format: BASE/FOLDER/ID.EXT
    return f"{CDN_BASE}/{path}/{asset_id}.{ext}"

def download_asset(asset_id, asset_type="char"):
    """Wiki first, then Official CDN fallback."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0'
    }

    # 1. CHECK WIKI FIRST
    url = get_wiki_image_by_id(asset_id, asset_type)
    source = "Wiki"

    # 2. CHECK CDN SECOND (If Wiki search returns None)
    if not url:
        url = get_official_cdn_url(asset_id, asset_type)
        source = "Official CDN"

    if not url:
        return None
        
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        
        # Local DB Naming: keep "char_" for MC so your UI finds it
        type_prefix = {"char": "char_", "summon": "summon_", "raid": "raid_"}
        prefix = type_prefix.get(asset_type, "char_")
        ext = "jpg" if asset_type == "raid" else "png"
        
        save_path = f"./db/{prefix}{asset_id}.{ext}"
        os.makedirs("./db", exist_ok=True)
        
        with open(save_path, "wb") as f:
            f.write(r.content)
            
        print(f"Done! Downloaded {asset_id} from {source} -> {save_path}")
        return save_path
        
    except Exception as e:
        print(f"Critical error downloading {asset_id}: {e}")
        return None
