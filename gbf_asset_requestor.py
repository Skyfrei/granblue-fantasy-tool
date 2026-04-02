import requests
import os
from lxml import html
import re


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

def clean_scraped_data(raw_attacks):
    cleaned_mechanics = []
    
    # Keywords that usually indicate a real boss mechanic
    mechanic_keywords = ["TR ", "Trigger", "HP ", "OD ", "Normal", "Special Attack"]
    
    # Keywords to EXCLUDE (Noise)
    noise_keywords = ["Estimated damage", "Relative to damage", "ATK Down", "Voice Actor", "magnificent", "bend the knee"]
    
    for entry in raw_attacks:
        # 1. Skip rows that are clearly part of the "Damage/Resistances" tables
        if any(noise in entry for noise in noise_keywords):
            continue
            
        # 2. Skip rows that are too short or just Japanese voice lines (usually contain | )
        if "|" in entry and len(entry) < 50 and not any(k in entry for k in ["Phase", "TR", "%"]):
            continue
    
        # 3. Keep rows that mention Triggers or Special Attacks
        if any(k in entry for k in mechanic_keywords):
            # Clean up extra newlines and spaces
            clean_entry = re.sub(r'\n+', '\n', entry).strip()
            cleaned_mechanics.append(clean_entry)
    
    return cleaned_mechanics

def scrape_raid_info(boss_name):
    # 1. Clean the name: Remove "Lvl 120 " or similar prefixes
    clean_name = re.sub(r'^Lvl\s+\d+\s+', '', boss_name).strip()
    # Replace spaces with underscores for the URL
    url_name = clean_name.replace(' ', '_')
    url = f"https://gbf.wiki/{url_name}_(Raid)"
    
    # 2. Headers are mandatory! 
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # FIX: Added headers=headers here
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Error: Received status {response.status_code} for URL: {url}")
            return {"attacks": [], "notes": ["Could not reach wiki page."]}

        tree = html.fromstring(response.content)
        
        # 3. Scrape Tables
        attacks = []
        # We target tables that look like raid mechanics
        tables = tree.xpath('//table[contains(@class, "wikitable")]')
        
        for table in tables:
            # Check if this specific table contains "Trigger" or "Special Attack" text
            table_text = "".join(table.xpath('.//th//text()')).lower()
            if any(word in table_text for word in ["trigger", "special", "attack", "effect"]):
                
                rows = table.xpath('.//tr[td]') # Only get rows that have data cells
                for row in rows:
                    # Get text from every cell in the row, including links and spans
                    cells = row.xpath('./td')
                    row_data = []
                    for cell in cells:
                        # This join/strip magic cleans up all nested tags inside the cell
                        text = " ".join(cell.xpath('.//text()')).strip()
                        if text:
                            row_data.append(text)
                    
                    if row_data:
                        attacks.append(" | ".join(row_data))

        # 4. Scrape Notes
        # Notes can be tricky; grabbing all text inside the <li> following the Notes span
        notes_list = tree.xpath('//span[@id="Notes"]/following::ul[1]/li')
        notes = [" ".join(li.xpath('.//text()')).strip() for li in notes_list]
        result = {
            "attacks": list(dict.fromkeys(attacks)), # Remove duplicates
            "notes": notes
        }

        return clean_scraped_data(result['attacks']) 

    except Exception as e:
        print(f"Scraper crashed: {e}")
        return {"attacks": [], "notes": [f"Error: {str(e)}"]}
