# -*- coding: utf-8 -*-
"""cardlib.py - Single card-data entry point for the analysis project."""

import json
import urllib.request
import urllib.parse
import core.card_db as card_db
import time

_INDEX = None

def load_index(verbose=False):
    """The shared card index, loaded once per process."""
    global _INDEX
    if _INDEX is None:
        try:
            _INDEX = card_db.get_index(verbose=verbose)
        except Exception as e:
            print(f"Warning: card index unavailable ({e}). Falling back to the Riftcodex API.")
            _INDEX = {}
    return _INDEX

def lookup(name, index=None):
    """Index entry for a card name, or None."""
    if not name:
        return None
    idx = index if index is not None else load_index()
    key = name.strip().lower()
    entry = idx.get(key)
    return entry

def _riftcodex_single(name):
    """Last resort for names the index does not carry."""
    headers = {
        "User-Agent": "RiftAnalyzer/1.0",
        "Accept": "application/json",
    }
    url = f"https://api.riftcodex.com/cards?name={urllib.parse.quote(name)}&limit=1"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            body = json.loads(res.read().decode("utf-8"))
            if body.get("items"):
                first_card = body["items"][0]
                first_name = first_card.get("name", "").lower()
                clean_name = (first_card.get("metadata") or {}).get("clean_name", "").lower()
                req_name = name.lower()
                if req_name in first_name or req_name in clean_name or first_name in req_name:
                    return card_db._flatten(first_card)
    except Exception as e:
        print(f"Warning: Riftcodex lookup failed for {name}: {e}")
    return None

def resolve(names, allow_network=True):
    """Resolves a list of card names."""
    idx = load_index()
    data, unresolved = {}, []
    for n in names:
        entry = lookup(n, idx)
        if entry is not None:
            data[n] = entry
        else:
            unresolved.append(n)

    if unresolved and allow_network:
        still = []
        for n in unresolved:
            entry = _riftcodex_single(n)
            if entry is not None:
                data[n] = entry
                time.sleep(0.1) # Be nice
            else:
                still.append(n)
        unresolved = still

    return data, unresolved
