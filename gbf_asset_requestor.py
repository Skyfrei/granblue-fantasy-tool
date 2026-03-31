import requests
import os

def get_wiki_image_by_id(char_id, asset_type="char"):
    api_url = "https://gbf.wiki/api.php"
    headers = {
        'User-Agent': 'GBF_DPS_Meter_Parser/1.0 (contact: your_discord_or_github)'
    }
    prefix = "Npc_s_" if asset_type == "char" else "Summon_m_"

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
        return f"https://gbf.wiki/Special:FilePath/{filename}"
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
    except requests.exceptions.JSONDecodeError:
        print("Received HTML instead of JSON. Check if you're being blocked.")
    return None

def wiki_dl_asset(char_id, asset_type="char"):
    url = get_wiki_image_by_id(char_id, asset_type)
    if not url:
        return None
    try:
        headers = {'User-Agent': 'GBF_DPS_Meter_Parser/1.0'}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        
        # Save it as ID.jpg in your db folder
        file_path = f"./db/{char_id}.jpg"
        with open(file_path, "wb") as f:
            f.write(r.content)
            
        print(f"Successfully downloaded icon for {char_id}")
        return file_path
    except Exception as e:
        print(f"Failed to download {char_id}: {e}")
        return None

def wiki_dl_char(char_id):
    return wiki_dl_asset(char_id, "char")

def wiki_dl_summon(summon_id):
    return wiki_dl_asset(summon_id, "summon")

if __name__ == "__main__":
    wiki_dl_char("3040379000_01")
