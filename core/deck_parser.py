# -*- coding: utf-8 -*-
"""
deck_parser.py - Deck Parser for Riftbound
Deterministic parsing of deck lists.
"""

import sys
import os
import re

# Load local database index
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import core.cardlib as cardlib
    CARD_DB = cardlib.load_index()
except Exception as e:
    print(f"Warning: Could not load local card index: {type(e).__name__}: {e}", file=sys.stderr)
    CARD_DB = {}


def clean_card_name(raw_line):
    line = raw_line.strip()
    if not line or line.startswith("//") or line.startswith("#"):
        return None, 0

    # Remove generic bracketed tags like [Deck], [Sideboard] if any
    line = re.sub(r'\s*\[[^\]]*\]\s*', ' ', line).strip()

    match = re.match(r'^(\d+)\s*x?\s+(.+)$', line, re.IGNORECASE)
    if match:
        qty = int(match.group(1))
        name = match.group(2).strip()
    else:
        qty = 1
        name = line.strip()

    return name, qty


def parse_deck_file(filepath):
    import json
    cards = []
    
    if filepath.endswith('.json'):
        with open(filepath, "r", encoding="utf-8") as f:
            deck_data = json.load(f)
            
        main_deck = deck_data.get("main_deck", {})
        for name, qty in main_deck.items():
            cards.append((name, qty))
        return cards
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()

    lines = content.splitlines()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("//") or stripped.startswith("#"):
            continue

        name, qty = clean_card_name(stripped)
        if not name:
            continue
            
        # Ignore Runes when parsing old text format to prevent breaking 40-card logic
        if "Rune" in name:
            continue

        cards.append((name, qty))

    return cards


UNRESOLVED_NAMES = []

def get_card_info(card_name):
    key = card_name.lower()
    if key in CARD_DB:
        return CARD_DB[key]

    # Dynamic API fallback
    try:
        entry = cardlib._riftcodex_single(card_name)
        if entry:
            CARD_DB[key] = entry
            return entry
    except Exception:
        pass

    if card_name not in UNRESOLVED_NAMES:
        UNRESOLVED_NAMES.append(card_name)
    return {
        "name": card_name,
        "type": "Unknown",
        "oracle_text": ""
    }
