import argparse
import json
import os
import re
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

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(ROOT_DIR, "data", "db")
INDEX_PATH = os.path.join(DB_DIR, "card_index.json")
TAGS_PATH = os.path.join(DB_DIR, "card_tags.json")
GLOSSARY_PATH = os.path.join(DB_DIR, "glossary.json")
SAMPLE_PATH = os.path.join(DB_DIR, "tag_sample.json")

EXAMPLE_NAMES = [
    "Noxus Hopeful",
    "Annie - Dark Child",
    "Master Yi - Meditative",
    "Vengeance",
    "Bewitching Spirit",
    "Charm",
]


def base_name(name):
    name = re.sub(r"\s*\([^)]*\)\s*", " ", name or "").strip()
    return re.sub(r"\s+", " ", name)


def load_json(path, default=None):
    if not os.path.exists(path):
        if default is not None:
            return default
        print(f"Missing {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_tags(tags_db):
    with open(TAGS_PATH, "w", encoding="utf-8") as handle:
        json.dump(tags_db, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def active_tags(glossary):
    return [name for name, info in glossary["tags"].items() if not info.get("retired")]


def group_index(cards):
    groups = {}
    for key, card in cards.items():
        groups.setdefault(base_name(card.get("name")).lower(), []).append((key, card))
    return groups


def canonical(items):
    return max(items, key=lambda item: len(item[1].get("oracle_text") or ""))


def build_prompt(batch, glossary, sample_by_name):
    names = active_tags(glossary)
    prompt = "You are an expert Riftbound card game analyst.\n"
    prompt += "Assign functional gameplay tags to the following cards.\n"
    prompt += f"Use ONLY these tags: {', '.join(names)}\n\n"
    prompt += "Rules:\n"
    for rule in glossary.get("tagging_rules", []):
        prompt += f"- {rule}\n"
    prompt += "\nDefinitions:\n"
    for name in names:
        info = glossary["tags"][name]
        prompt += f"- {name}: {info['summary']} Apply when: {info['apply_when']} Do not apply when: {info['do_not_apply_when']}\n"
    prompt += "\nExamples:\n"
    for name in EXAMPLE_NAMES:
        entry = sample_by_name.get(name)
        if entry:
            prompt += f"- {name}: {', '.join(entry['tags']) or '(no functional tag)'}\n"
    prompt += "\nCards:\n"
    for _key, card in batch:
        prompt += f"Name: {card.get('name', 'Unknown')}\n"
        prompt += f"Type: {card.get('type', '')} | Supertype: {card.get('supertype', '')}\n"
        prompt += f"Cost: {card.get('energy', 0)} Energy, {card.get('power', 0)} Power Burn\n"
        prompt += f"Stats: {card.get('might', 0)} Might\n"
        prompt += f"Text: {card.get('oracle_text', '')}\n\n"
    return prompt


def sanitize(tags, glossary):
    legal = set(active_tags(glossary))
    roles = [name for name in legal if glossary["tags"][name].get("role")]
    cleaned = []
    used_role = False
    for tag in tags:
        if tag not in legal or tag in cleaned:
            continue
        if tag in roles:
            if used_role:
                continue
            used_role = True
        cleaned.append(tag)
    return cleaned


class CardTags(BaseModel):
    name: str = Field(description="The exact name of the card.")
    tags: List[str] = Field(description="Functional tags chosen from the allowed list.")


class TagResponse(BaseModel):
    cards: List[CardTags]


def prepare_queue(cards, tags_db):
    """Copy tags onto untagged reprints. Return canonical cards that still need the API."""
    groups = group_index(cards)
    copied = 0
    queue = []
    for items in groups.values():
        cards_only = [card for _key, card in items]
        if any(card.get("supertype") in ("Basic", "Token") for card in cards_only):
            if all(card.get("supertype") in ("Basic", "Token") for card in cards_only):
                continue
        tagged = [(key, tags_db[key]) for key, _card in items if key in tags_db]
        if tagged:
            chosen = tagged[0][1]
            for key, _card in items:
                if key not in tags_db:
                    tags_db[key] = list(chosen)
                    copied += 1
            continue
        queue.append(canonical(items))
    return queue, copied


def main():
    parser = argparse.ArgumentParser(description="Tag untagged Riftbound cards with Gemini.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum new cards to send to the API.")
    parser.add_argument("--dry-run", action="store_true", help="Show the queue without calling the API.")
    args = parser.parse_args()

    glossary = load_json(GLOSSARY_PATH)
    cards = load_json(INDEX_PATH).get("cards", {})
    tags_db = load_json(TAGS_PATH, default={})
    sample = load_json(SAMPLE_PATH, default={"cards": []})
    sample_by_name = {entry["name"]: entry for entry in sample.get("cards", [])}

    queue, copied = prepare_queue(cards, tags_db)
    if copied and not args.dry_run:
        save_tags(tags_db)
    print(f"Copied tags onto {copied} reprints.")
    print(f"Untagged cards: {len(queue)}")
    if args.limit is not None:
        queue = queue[:args.limit]
        print(f"This run will tag: {len(queue)}")
    if args.dry_run or not queue:
        return

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Set it before running this script: GEMINI_API_KEY=your_key python scripts/ai_tagger.py")
        sys.exit(1)

    client = genai.Client()
    legal_names = active_tags(glossary)
    batch_size = 25
    for start in range(0, len(queue), batch_size):
        batch = queue[start:start + batch_size]
        print(f"Processing batch {start // batch_size + 1}/{(len(queue) + batch_size - 1) // batch_size}...")
        prompt = build_prompt(batch, glossary, sample_by_name)
        while True:
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=TagResponse,
                        temperature=0.1,
                    ),
                )
                result = response.parsed or TagResponse.model_validate_json(response.text)
                groups = group_index(cards)
                for card_res in result.cards:
                    matched = None
                    for key, card in batch:
                        if card.get("name", "").lower() == card_res.name.lower():
                            matched = (key, card)
                            break
                    if matched is None:
                        print(f"Unmatched model result: {card_res.name}")
                        continue
                    cleaned = sanitize(card_res.tags, glossary)
                    for sibling_key, _sibling in groups[base_name(matched[1].get("name")).lower()]:
                        tags_db[sibling_key] = list(cleaned)
                save_tags(tags_db)
                print(f"Saved {len(result.cards)} cards. Allowed tags: {', '.join(legal_names[:4])}...")
                break
            except Exception as exc:
                err_str = str(exc)
                print(f"Error processing batch: {err_str}")
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                    if "retry in" in err_str and "h" in err_str:
                        print("Daily quota exhausted. Run the script again later.")
                        sys.exit(1)
                    print("Rate limit hit. Waiting 60 seconds...")
                    time.sleep(60)
                else:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
        time.sleep(2)

    print("Tagging process complete.")


if __name__ == "__main__":
    main()
