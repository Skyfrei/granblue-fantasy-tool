import requests
import os
from lxml import html
import re
import sys

CDN_BASE = "https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/assets"

CDN_PATH_MAP = {
    "char": "npc/s",
    "summon": "summon/b",
    "raid": "quest/l",
    "leader": "leader/pm", # MC Classes/Skins
    "weapon": "weapon/ls"
}

def get_persistent_db():
    if getattr(sys, 'frozen', False):
        # Running as .exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as .py
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    db_path = os.path.join(base_dir, "db")
    os.makedirs(db_path, exist_ok=True)
    return db_path

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

    ext = "jpg" if asset_type in ("raid", "weapon") else "png"
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
        type_prefix = {"char": "char_", "summon": "summon_", "raid": "raid_", "weapon": "weapon_"}
        prefix = type_prefix.get(asset_type, "char_")
        ext = "jpg" if asset_type in ("raid", "weapon") else "png"
        

        filename = f"{prefix}{asset_id}.{ext}"
        save_path = os.path.join(get_persistent_db(), filename)
        
        with open(save_path, "wb") as f:
            f.write(r.content)
            
        return save_path
        
    except Exception as e:
        print(f"Critical error downloading {asset_id}: {e}")
        return None

def scrape_raid_info(boss_name):
    clean_name = re.sub(r'^Lvl\s+\d+\s+', '', boss_name).strip()
    url_name = clean_name.replace(' ', '_')
    url = f"https://gbf.wiki/{url_name}_(Raid)"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Error: Received status {response.status_code} for URL: {url}")
            return {"attacks": [], "notes": ["Could not reach wiki page."]}

        tree = html.fromstring(response.content)
        
        result = dict()
        tables = tree.xpath('//table[contains(@class, "wikitable")]')
        current_key = ""

        for table in tables:
            # Check if this specific table contains "Trigger" or "Special Attack" text
            table_text = "".join(table.xpath('.//th//text()')).lower()
            if any(word in table_text for word in ["trigger", "special", "attack", "effect"]):
                
                rows = table.xpath('.//tr[td]') # Only get rows that have data cells
                for row in rows:
                    cells = row.xpath('./td')
                    row_data = []
                    for cell in cells:
                        colspan = int(cell.get('colspan', 1))
                        for child in cell:
                            if child.tag == 'ul':
                                ul_text = " ".join(child.xpath('.//text()')).strip()
                                current_key = ul_text
                                if colspan not in result:
                                    result[colspan] = {}

                                base_key = current_key
                                counter = 2
                                while current_key in result[colspan]:
                                    current_key = f"{base_key}{counter}"
                                    counter += 1
                                
                                result[colspan][current_key] = []

                            elif child.tag == 'dl':
                                for dd in child.xpath('.//dd[not(parent::dd)]'):  # avoid nested dd
                                    dd_text = " ".join(dd.xpath('.//text()')).strip()
                                    if dd_text and current_key:
                                        result[colspan][current_key].append(dd_text)

        return result

    except Exception as e:
        print(f"Scraper crashed: {e}")
        return {"attacks": [], "notes": [f"Error: {str(e)}"]}
