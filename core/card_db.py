# -*- coding: utf-8 -*-
"""card_db.py - Riftcodex database updater and offline caching system."""

import json
import os
import datetime
import urllib.request
import urllib.parse
import time

# Resolve paths relative to the project root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(ROOT_DIR, "data", "db")
SOURCE_DB = os.path.join(DB_DIR, "cards.json")
INDEX_PATH = os.path.join(DB_DIR, "card_index.json")

INDEX_VERSION = 1

def fetch_riftcodex_cards(verbose=False):
    """Fetches all cards from Riftcodex API with pagination."""
    all_cards = []
    page = 1
    total_pages = 1
    headers = {'User-Agent': 'RiftAnalyzer/1.0', 'Accept': 'application/json'}
    
    while page <= total_pages:
        if verbose:
            print(f"Fetching page {page} of {total_pages if total_pages > 1 else '?'}...")
        
        url = f"https://api.riftcodex.com/cards?page={page}&size=100"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode('utf-8'))
                
            if 'items' in data:
                all_cards.extend(data['items'])
            
            total_pages = data.get('pages', 1)
            page += 1
            time.sleep(0.1) # Be nice to the API
        except Exception as e:
            if verbose:
                print(f"Error fetching page {page}: {e}")
            break
            
    return all_cards

def update_db(force=False, verbose=False):
    """Downloads Riftcodex bulk data if older than 7 days, with offline fallback."""
    os.makedirs(DB_DIR, exist_ok=True)
    
    needs_download = True
    if not force and os.path.exists(SOURCE_DB):
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(SOURCE_DB))
        if (datetime.datetime.now() - mtime).days < 7:
            needs_download = False

    if needs_download:
        if verbose:
            print("Checking Riftcodex for card updates...")
        
        cards = fetch_riftcodex_cards(verbose=verbose)
        if cards:
            with open(SOURCE_DB, 'w', encoding='utf-8') as f:
                json.dump(cards, f, ensure_ascii=False)
            
            if verbose:
                print(f"Downloaded {len(cards)} cards successfully.")
            
            # Rebuild index automatically after a fresh download
            build_index(verbose=verbose)
        else:
            if verbose:
                print("Failed to download cards. Falling back to existing offline cache if available.")
    else:
        if verbose:
            print("Local DB is fresh (<7 days old).")

def _flatten(card):
    """Collapses a Riftcodex card into the fields the analyzer reads."""
    classification = card.get("classification", {})
    text_data = card.get("text", {})
    attributes = card.get("attributes", {})
    
    entry = {
        "name": card.get("name"),
        "type": classification.get("type", ""),
        "supertype": classification.get("supertype", ""),
        "rarity": classification.get("rarity", ""),
        "domains": classification.get("domain", []),
        "oracle_text": text_data.get("plain", "") if text_data else "",
        "energy": attributes.get("energy", 0) if attributes else 0,
        "might": attributes.get("might", 0) if attributes else 0,
        "power": attributes.get("power", 0) if attributes else 0,
        "set": card.get("set", {}).get("set_id", ""),
        "collector_number": card.get("collector_number", "")
    }

    return entry


def build_index(verbose=False):
    """Reads the full Riftcodex dump once and writes the slim keyed index."""
    if not os.path.exists(SOURCE_DB):
        if verbose:
            print("Source DB not found, cannot build index.")
        return {}
        
    with open(SOURCE_DB, "r", encoding="utf-8") as f:
        cards = json.load(f)

    index = {}
    for card in cards:
        name = card.get("name")
        if not name:
            continue
            
        entry = _flatten(card)
        key = name.lower()
        
        # In Riftcodex, some cards have (Metal) or similar in the name, we might want to index both
        if key not in index:
            index[key] = entry

        # Clean name fallback
        metadata = card.get("metadata") or {}
        clean_name = metadata.get("clean_name") or ""
        clean_name = clean_name.lower()
        if clean_name and clean_name not in index:
            index[clean_name] = entry

    payload = {"version": INDEX_VERSION, "cards": index}
    tmp = INDEX_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, INDEX_PATH)

    if verbose:
        size = os.path.getsize(INDEX_PATH) / 1e6
        src_size = os.path.getsize(SOURCE_DB) / 1e6
        print(f"Card index built: {len(index)} keys, {size:.1f} MB (source dump {src_size:.1f} MB)")
    return index


def get_index(verbose=False):
    """Returns the index, rebuilding it if missing or stale."""
    # Ensure update is attempted before giving up
    update_db(verbose=verbose)
    
    if not os.path.exists(SOURCE_DB):
        return {}

    needs_build = True
    if os.path.exists(INDEX_PATH) and os.path.getmtime(INDEX_PATH) >= os.path.getmtime(SOURCE_DB):
        try:
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if payload.get("version") == INDEX_VERSION:
                return payload.get("cards", {})
        except Exception:
            pass  # Corrupt or truncated index: fall through and rebuild it.

    if needs_build:
        return build_index(verbose=verbose)
    return {}

if __name__ == "__main__":
    update_db(force=True, verbose=True)
