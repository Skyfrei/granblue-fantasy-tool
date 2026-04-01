import requests
import os

def get_wiki_image_by_id(char_id, asset_type="char"):
    api_url = "https://gbf.wiki/api.php"
    headers = {
        'User-Agent': 'GBF-Tool/1.0'
    }
    
    # ── Prefix Mapping ──
    if asset_type == "char":
        prefix = "Npc_s_" 
    elif asset_type == "summon":
        prefix = "Summon_m_"
    elif asset_type == "raid":
        prefix = "Quest_l_" # "l" is the standard banner size
    else:
        prefix = ""

    params = {
        "action": "query",
        "format": "json",
        "list": "allimages",
        "aifrom": f"{prefix}{char_id}", 
        "ailimit": 1
    }
    
    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status() 
        data = response.json()
        images = data.get('query', {}).get('allimages', [])
        
        if not images:
            return None
            
        filename = images[0]['name']
        
        if str(char_id) not in filename:
            return None

        return f"https://gbf.wiki/Special:FilePath/{filename}"
        
    except Exception as e:
        print(f"Metadata Error: {e}")
    return None

def wiki_dl_asset(char_id, asset_type="char"):
    url = get_wiki_image_by_id(char_id, asset_type)
    if not url:
        print(f"Could not find URL for {asset_type} ID: {char_id}")
        return None
        
    try:
        headers = {'User-Agent': 'GBF_DPS_Meter_Parser/1.0'}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        
        # ── Specialized Naming ──
        # We add a prefix to the local filename so your DB stays organized
        prefix_map = {"char": "", "summon": "summon_", "raid": "quest_"}
        save_name = f"{prefix_map.get(asset_type, '')}{char_id}.jpg"
        file_path = f"./db/{save_name}"
        
        os.makedirs("./db", exist_ok=True) # Ensure folder exists
        
        with open(file_path, "wb") as f:
            f.write(r.content)
            
        print(f"Successfully downloaded {asset_type} icon: {save_name}")
        return file_path
        
    except Exception as e:
        print(f"Failed to download {char_id}: {e}")
        return None

def wiki_dl_char(char_id):
    return wiki_dl_asset(char_id, "char")

def wiki_dl_summon(summon_id):
    return wiki_dl_asset(summon_id, "summon")

def wiki_dl_raid(quest_id):
    return wiki_dl_asset(quest_id, "raid")



if __name__ == "__main__":
    wiki_dl_char("3040379000_01")
