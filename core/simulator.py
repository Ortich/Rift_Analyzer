import json
import os
import random

def get_bot_deck(archetype):
    deck = []
    if archetype == "Aggro":
        for _ in range(20): deck.append({"energy": 1, "burn": 0, "type": "Units", "might": 2, "spell_value": 0})
        for _ in range(15): deck.append({"energy": 2, "burn": 0, "type": "Units", "might": 4, "spell_value": 0})
        for _ in range(5):  deck.append({"energy": 2, "burn": 0, "type": "Spells", "might": 0, "spell_value": 4})
    elif archetype == "Midrange":
        for _ in range(5):  deck.append({"energy": 2, "burn": 0, "type": "Units", "might": 3, "spell_value": 0})
        for _ in range(15): deck.append({"energy": 3, "burn": 0, "type": "Units", "might": 5, "spell_value": 0})
        for _ in range(10): deck.append({"energy": 4, "burn": 0, "type": "Units", "might": 7, "spell_value": 0})
        for _ in range(5):  deck.append({"energy": 5, "burn": 0, "type": "Units", "might": 9, "spell_value": 0})
        for _ in range(5):  deck.append({"energy": 3, "burn": 0, "type": "Spells", "might": 0, "spell_value": 5})
    elif archetype == "Control":
        for _ in range(15): deck.append({"energy": 2, "burn": 0, "type": "Spells", "might": 0, "spell_value": 4})
        for _ in range(10): deck.append({"energy": 4, "burn": 0, "type": "Spells", "might": 0, "spell_value": 8})
        for _ in range(5):  deck.append({"energy": 6, "burn": 0, "type": "Spells", "might": 0, "spell_value": 12})
        for _ in range(10): deck.append({"energy": 8, "burn": 0, "type": "Units", "might": 14, "spell_value": 0})
    return deck

def ai_play_turn(hand, current_energy, max_energy, my_units, enemy_units):
    hand.sort(key=lambda x: x.get("energy", 0), reverse=True)
    played_cards = []
    
    for card in list(hand):
        energy_cost = card.get("energy", 0)
        burn_cost = card.get("burn", 0)
        if energy_cost <= current_energy and burn_cost <= max_energy:
            
            if card.get("type") in ["Spells", "Equipments"]:
                spell_val = card.get("spell_value", energy_cost * 1.5)
                target = None
                if enemy_units:
                    kills = [u for u in enemy_units if u["current_might"] <= spell_val]
                    if kills:
                        target = max(kills, key=lambda x: x["current_might"])
                    else:
                        target = max(enemy_units, key=lambda x: x["current_might"])
                        
                if target is None and card.get("type") == "Spells":
                    continue
                elif target:
                    target["current_might"] -= spell_val
                    if target["current_might"] <= 0:
                        enemy_units.remove(target)
                        
            elif card.get("type") == "Units":
                my_units.append({
                    "max_might": card.get("might", 0),
                    "current_might": card.get("might", 0)
                })
                
            current_energy -= energy_cost
            max_energy -= burn_cost
            played_cards.append(card)
            hand.remove(card)
            
    return max_energy

def draw_starting_hand(deck):
    random.shuffle(deck)
    hand = deck[:4]
    deck = deck[4:]
    keep = []
    discard = []
    for c in hand:
        if c.get("energy", 0) <= 3:
            keep.append(c)
        else:
            discard.append(c)
    if discard:
        deck.extend(discard)
        random.shuffle(deck)
        hand.extend(deck[:len(discard)])
        deck = deck[len(discard):]
    return hand, deck

def simulate_game(deck_p1_orig, deck_p2_orig, p1_starts):
    deck_p1 = deck_p1_orig.copy()
    deck_p2 = deck_p2_orig.copy()
    
    hand_p1, deck_p1 = draw_starting_hand(deck_p1)
    hand_p2, deck_p2 = draw_starting_hand(deck_p2)
        
    vp_p1 = 0
    vp_p2 = 0
    units_p1 = []
    units_p2 = []
    
    max_energy_p1 = 0
    max_energy_p2 = 0
    
    for turn in range(1, 15):
        # --- PLAYER 1 TURN ---
        if turn == 1 and p1_starts:
            pass
        else:
            if deck_p1: hand_p1.append(deck_p1.pop(0))
                
        while len(hand_p1) > 10:
            hand_p1.sort(key=lambda x: x.get("energy", 0))
            hand_p1.pop()
            
        max_energy_p1 = min(max_energy_p1 + (2 if not (turn == 1 and not p1_starts) else 3), 12)
        max_energy_p1 = ai_play_turn(hand_p1, max_energy_p1, max_energy_p1, units_p1, units_p2)

        # --- PLAYER 2 TURN ---
        if turn == 1 and not p1_starts:
            pass
        else:
            if deck_p2: hand_p2.append(deck_p2.pop(0))
                
        while len(hand_p2) > 10:
            hand_p2.sort(key=lambda x: x.get("energy", 0))
            hand_p2.pop()
            
        max_energy_p2 = min(max_energy_p2 + (2 if not (turn == 1 and p1_starts) else 3), 12)
        max_energy_p2 = ai_play_turn(hand_p2, max_energy_p2, max_energy_p2, units_p2, units_p1)

        # --- COMBAT PHASE ---
        p1_lanes = [0, 0, 0]
        p2_lanes = [0, 0, 0]
        
        for u in units_p1: p1_lanes[random.randint(0, 2)] += u["current_might"]
        for u in units_p2: p2_lanes[random.randint(0, 2)] += u["current_might"]
            
        for p1, p2 in zip(p1_lanes, p2_lanes):
            if p1 > p2: vp_p1 += 1
            elif p2 > p1: vp_p2 += 1
                
        if vp_p1 >= 8 or vp_p2 >= 8:
            break
            
        # --- END PHASE ---
        for u in units_p1: u["current_might"] = u["max_might"]
        for u in units_p2: u["current_might"] = u["max_might"]
            
    return vp_p1 >= vp_p2

def run_pvp_simulation(parsed_deck_path, iterations=1000):
    if not os.path.exists(parsed_deck_path):
        print(f"Error: Parsed deck file '{parsed_deck_path}' not found.")
        return None
        
    with open(parsed_deck_path, "r", encoding="utf-8") as f:
        deck_data = json.load(f)
        
    print(f"--- Running Viktor's Deck Simulation (Symmetric PvP Engine - {iterations} iterations) ---")
    
    virtual_deck = deck_data.get("virtual_deck_costs", [])
    
    # Pad deck if < 40
    while len(virtual_deck) < 40:
        virtual_deck.append({"energy": 2, "burn": 0, "type": "Units", "might": 2, "spell_value": 0})
        
    results = {}
    archetypes = ["Aggro", "Control", "Midrange"]
    
    for archetype in archetypes:
        wins = 0
        bot_deck = get_bot_deck(archetype)
        
        for _ in range(iterations):
            p1_wins = 0
            p2_wins = 0
            
            if simulate_game(virtual_deck, bot_deck, True): p1_wins += 1
            else: p2_wins += 1
            
            if simulate_game(virtual_deck, bot_deck, False): p1_wins += 1
            else: p2_wins += 1
            
            if p1_wins == 1 and p2_wins == 1:
                if simulate_game(virtual_deck, bot_deck, True): p1_wins += 1
                else: p2_wins += 1
                
            if p1_wins == 2:
                wins += 1
                
        win_rate = (wins / iterations) * 100
        results[archetype] = round(win_rate, 2)
        print(f"Win Rate vs {archetype}: {results[archetype]}%")
        
    avg_win_rate = sum(results.values()) / 3
    results["average_win_rate"] = round(avg_win_rate, 2)
    print(f"Overall Average Win Rate: {results['average_win_rate']}%\n")
    
    return results

if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "db", "parsed_deck.json")
    run_pvp_simulation(db_path)
