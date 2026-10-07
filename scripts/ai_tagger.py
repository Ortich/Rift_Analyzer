import json
import os
import sys
import time
from typing import List
from pydantic import BaseModel, Field

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Please install google-genai: pip install google-genai pydantic")
    sys.exit(1)

# Resolve paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(ROOT_DIR, "data", "db")
INDEX_PATH = os.path.join(DB_DIR, "card_index.json")
TAGS_PATH = os.path.join(DB_DIR, "card_tags.json")

# Taxonomy of expected functional tags
AVAILABLE_TAGS = [
    "Removal", "AoE", "Card Draw", "Ramp", "Finisher", 
    "Heal/Shield", "Combat Trick", "Value Engine", "Token Generator", 
    "Hand Disruption", "Trash Synergy", "Aggro", "Control", 
    "Midrange", "Combo", "Discard", "Direct Damage"
]

class CardTags(BaseModel):
    name: str = Field(description="The exact name of the card.")
    tags: List[str] = Field(description=f"List of functional tags chosen from {AVAILABLE_TAGS}")

class TagResponse(BaseModel):
    cards: List[CardTags]

def load_data():
    if not os.path.exists(INDEX_PATH):
        print(f"Index not found at {INDEX_PATH}. Please run core/card_db.py first.")
        sys.exit(1)
        
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        index_data = json.load(f)
        
    cards = index_data.get("cards", {})
    
    tags_db = {}
    if os.path.exists(TAGS_PATH):
        with open(TAGS_PATH, 'r', encoding='utf-8') as f:
            tags_db = json.load(f)
            
    return cards, tags_db

def save_tags(tags_db):
    with open(TAGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(tags_db, f, indent=2, ensure_ascii=False)

def build_prompt(batch):
    prompt = "You are an expert Riftbound card game analyst.\n"
    prompt += "Your task is to assign functional gameplay tags to the following cards.\n"
    prompt += f"Use ONLY the following tags (you can assign multiple per card): {', '.join(AVAILABLE_TAGS)}\n\n"
    prompt += "Definitions:\n"
    prompt += "- Removal: Destroys, deals damage to, or exiles enemy units.\n"
    prompt += "- AoE: Area of Effect, affects multiple units or battlefields.\n"
    prompt += "- Card Draw: Draws cards from the deck.\n"
    prompt += "- Ramp: Generates extra energy, runes, or discounts costs.\n"
    prompt += "- Finisher: High cost/impact cards that win the game, high Might or unblockable damage.\n"
    prompt += "- Heal/Shield: Provides shielding, healing, or protection.\n"
    prompt += "- Combat Trick: Spells/Actions played during combat to change stats, e.g. +Might.\n"
    prompt += "- Value Engine: Generates repeated advantage over time, tokens, or draws.\n"
    prompt += "- Token Generator: Creates token units or gear.\n"
    prompt += "- Hand Disruption: Forces discard or messes with opponent's hand.\n"
    prompt += "- Trash Synergy: Interacts with the trash/graveyard, recursion.\n"
    prompt += "- Aggro: Low cost, aggressive cards suitable for fast decks.\n"
    prompt += "- Control: Slow, defensive cards, sweepers, late-game answers.\n"
    prompt += "- Midrange: Efficient cost-to-stats ratio, flexible cards.\n"
    prompt += "- Combo: Cards that rely heavily on specific synergies.\n\n"
    
    prompt += "Here are the cards:\n"
    for key, card in batch:
        prompt += f"Name: {card.get('name', 'Unknown')}\n"
        prompt += f"Type: {card.get('type', '')} | Supertype: {card.get('supertype', '')}\n"
        prompt += f"Cost: {card.get('energy', 0)} Energy, {card.get('power', 0)} Power Burn\n"
        prompt += f"Stats: {card.get('might', 0)} Might\n"
        prompt += f"Text: {card.get('oracle_text', '')}\n\n"
        
    return prompt

def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please set it before running this script: set GEMINI_API_KEY=your_key")
        sys.exit(1)
        
    client = genai.Client()
    cards, tags_db = load_data()
    
    untagged = []
    # Identify untagged cards. Skip basic runes and tokens.
    for key, card in cards.items():
        if key not in tags_db:
            if card.get("supertype") in ("Basic", "Token"):
                continue
            untagged.append((key, card))
            
    if not untagged:
        print("All cards are already tagged!")
        return

    print(f"Found {len(untagged)} untagged cards. Preparing to process...")
    
    batch_size = 25
    for i in range(0, len(untagged), batch_size):
        batch = untagged[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(untagged) + batch_size - 1)//batch_size}...")
        
        prompt = build_prompt(batch)
        
        while True:
            try:
                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=TagResponse,
                        temperature=0.1
                    )
                )
                
                result = response.parsed
                if not result:
                    result = TagResponse.model_validate_json(response.text)
                    
                for card_res in result.cards:
                    matched_key = None
                    for k, c in batch:
                        if c.get('name', '').lower() == card_res.name.lower():
                            matched_key = k
                            break
                            
                    if matched_key:
                        tags_db[matched_key] = card_res.tags
                    else:
                        tags_db[card_res.name.lower()] = card_res.tags
                        
                save_tags(tags_db)
                print(f"Saved {len(result.cards)} tags.")
                break # Exit the retry loop on success
                
            except Exception as e:
                err_str = str(e)
                print(f"Error processing batch: {err_str}")
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                    if "retry in" in err_str and "h" in err_str:
                        print("Daily quota exhausted. Please run the script again tomorrow or upgrade your API key billing.")
                        sys.exit(1)
                    print("Rate limit hit. Waiting 60 seconds...")
                    time.sleep(60)
                else:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
            
        time.sleep(2) # Be nice to the API

    print("Tagging process complete.")

if __name__ == '__main__':
    main()
