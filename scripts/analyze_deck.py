import sys
import os
import argparse
import json
import re
from collections import defaultdict

# Ensure the core module is accessible
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.deck_parser as deck_parser

KEYWORDS = [
    "Shield", "Barrier", "Overwhelm", "Pierce", "Ambush", "Stealth", 
    "Rally", "Ready", "Accelerate", "Ramp", "Draw", "Cycle", "Recall", 
    "Return", "Stun", "Vulnerable", "Frostbite", "Freeze", "Bleed",
    "Trash", "Scrap", "Banish", "Exile", "Sacrifice", "Consume", "Bounce",
    "Mill", "Purge", "Elusive", "Defender", "Sentinel", "First Strike",
    "Quick Attack", "Exhaust", "Slay", "Execute", "Cascade", "Discover",
    "Affinity", "Decay", "Silence", "Nullify"
]

def analyze_deck(filepath):
    if not os.path.exists(filepath):
        print(json.dumps({"error": f"Deck file '{filepath}' not found."}, indent=2))
        return

    cards_in_deck = deck_parser.parse_deck_file(filepath)
    if not cards_in_deck:
        print(json.dumps({"error": "Deck is empty or invalid."}, indent=2))
        return

    main_deck_size = 0
    valid_format = True
    type_breakdown = defaultdict(int)
    domain_counts = defaultdict(int)
    energy_curve = {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5+": 0}
    
    total_might = 0
    total_burn_cost = 0
    unit_count = 0
    non_champion_count = 0
    
    keyword_density = defaultdict(int)
    unresolved_cards = []
    virtual_deck_costs = []

    for name, qty in cards_in_deck:
        info = deck_parser.get_card_info(name)
        
        if info.get("type") == "Unknown":
            unresolved_cards.append({"name": name, "qty": qty})
            main_deck_size += qty
            if qty > 3: valid_format = False
            continue
            
        card_type = info.get("type", "Unknown").lower()
        supertype = info.get("supertype", "").lower() if info.get("supertype") else ""
        
        # Categorize Type
        if "champion" in card_type or "nexus" in card_type or "champion" in supertype or "legend" in card_type or "legend" in supertype or "legend" in info.get("rarity", "").lower():
            main_type = "Champion/Legend"
            # Champions/Legends sit outside the 40-card main deck
        elif "unit" in card_type or "creature" in card_type:
            main_type = "Units"
            main_deck_size += qty
            if qty > 3: valid_format = False
        elif "spell" in card_type or "action" in card_type:
            main_type = "Spells"
            main_deck_size += qty
            if qty > 3: valid_format = False
        elif "equipment" in card_type or "attachment" in card_type or "gear" in card_type:
            main_type = "Equipments"
            main_deck_size += qty
            if qty > 3: valid_format = False
        elif "landmark" in card_type or "shrine" in card_type:
            main_type = "Landmarks"
            main_deck_size += qty
            if qty > 3: valid_format = False
        else:
            main_type = card_type.title()
            main_deck_size += qty
            if qty > 3: valid_format = False
                
        type_breakdown[main_type] += qty
        
        # Domains
        domains = info.get("domains", [])
        if domains:
            for d in domains:
                domain_counts[d] += qty
                
        # Energy and Burn Cost (only for main deck)
        if main_type != "Champion/Legend":
            energy = info.get("energy", 0)
            burn = info.get("power", 0) # In Riftbound, 'power' is actually Energy Burn cost
            
            try:
                energy_val = int(energy)
            except (ValueError, TypeError):
                energy_val = 0
                
            try:
                burn_val = int(burn)
            except (ValueError, TypeError):
                burn_val = 0
                
            if energy_val >= 5:
                energy_curve["5+"] += qty
            else:
                energy_curve[str(energy_val)] += qty
                
            total_burn_cost += burn_val * qty
            non_champion_count += qty
            
            for _ in range(qty):
                card_might = 0
                spell_value = 0
                if main_type == "Units":
                    try:
                        card_might = int(info.get("might", 0))
                    except (ValueError, TypeError):
                        pass
                elif main_type in ["Spells", "Equipments"]:
                    oracle_text = info.get("text", {}).get("plain", "")
                    if oracle_text:
                        match = re.search(r'(?i)(?:\+|\-|deal |assault )(\d+)', oracle_text)
                        if match:
                            spell_value = int(match.group(1))
                        else:
                            spell_value = int(energy_val * 1.5)
                    else:
                        spell_value = int(energy_val * 1.5)
                        
                virtual_deck_costs.append({
                    "energy": energy_val, 
                    "burn": burn_val, 
                    "type": main_type, 
                    "might": card_might,
                    "spell_value": spell_value
                })
                
        # Combat Stats (Only for Units)
        if main_type == "Units":
            might = info.get("might", 0)
            try:
                m_val = int(might)
                total_might += m_val * qty
                unit_count += qty
            except (ValueError, TypeError):
                pass
                
        # Keywords
        oracle_text = info.get("oracle_text", "")
        if oracle_text:
            for kw in KEYWORDS:
                # match whole word, case insensitive
                if re.search(r'\b' + re.escape(kw) + r'\b', oracle_text, re.IGNORECASE):
                    keyword_density[kw] += qty

    if main_deck_size != 40:
        valid_format = False
        
    if len(domain_counts) > 2:
        valid_format = False

    avg_might = round(total_might / unit_count, 2) if unit_count > 0 else 0
    avg_burn = round(total_burn_cost / non_champion_count, 2) if non_champion_count > 0 else 0

    output = {
        "deck_size": main_deck_size,
        "valid_format": valid_format,
        "domains": dict(domain_counts),
        "energy_curve": energy_curve,
        "type_breakdown": dict(type_breakdown),
        "average_might": avg_might,
        "average_burn_cost": avg_burn,
        "keyword_density": dict(keyword_density),
        "virtual_deck_costs": virtual_deck_costs
    }
    
    if unresolved_cards:
        output["unresolved_cards"] = unresolved_cards
        
    # Phase 1 Output
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "db", "parsed_deck.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        
    print(f"Phase 1 complete. Saved parsed data to {output_path}")
    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a Riftbound decklist.")
    parser.add_argument("deck_file", help="Path to the decklist text file.")
    args = parser.parse_args()
    
    analyze_deck(args.deck_file)
