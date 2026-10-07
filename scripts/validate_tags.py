"""Check the calibration sample against the glossary and the tag index."""

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB = os.path.join(ROOT, "data", "db")
INDEX_PATH = os.path.join(DB, "card_index.json")
TAGS_PATH = os.path.join(DB, "card_tags.json")
GLOSSARY_PATH = os.path.join(DB, "glossary.json")
SAMPLE_PATH = os.path.join(DB, "tag_sample.json")

ROLE_TAGS = ("Aggro", "Control", "Midrange", "Combo")


def base_name(name):
    name = re.sub(r"\s*\([^)]*\)\s*", " ", name or "").strip()
    return re.sub(r"\s+", " ", name).lower()


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main():
    glossary = load(GLOSSARY_PATH)
    sample = load(SAMPLE_PATH)
    tags_db = load(TAGS_PATH)
    index = load(INDEX_PATH)["cards"]

    legal = {name for name, info in glossary["tags"].items() if not info.get("retired")}
    errors = []
    cards = sample["cards"]
    if len(cards) != 100:
        errors.append(f"sample has {len(cards)} cards, expected 100")
    if len({c["name"].lower() for c in cards}) != len(cards):
        errors.append("sample has duplicate names")

    groups = {}
    for key, card in index.items():
        groups.setdefault(base_name(card.get("name")), []).append(key)

    for entry in cards:
        name = entry["name"]
        tags = entry["tags"]
        unknown = [tag for tag in tags if tag not in legal]
        if unknown:
            errors.append(f"{name}: unknown tags {unknown}")
        roles = [tag for tag in tags if tag in ROLE_TAGS]
        if len(roles) > 1:
            errors.append(f"{name}: more than one role {roles}")
        if "Ramp" in tags or "Midrange" in tags:
            errors.append(f"{name}: uses a retired or default role")
        keys = groups.get(name.lower(), [])
        if not keys:
            errors.append(f"{name}: not in the card index")
            continue
        for key in keys:
            if tags_db.get(key) != tags:
                errors.append(f"{name}: index key {key!r} has {tags_db.get(key)!r}")
                break

    # Boundaries the sample is meant to teach.
    by_name = {c["name"]: c["tags"] for c in cards}
    if "Rune Generation" in by_name["Master Yi - Meditative"]:
        errors.append("Master Yi - Meditative must not be Rune Generation")
    if "Rune Generation" not in by_name["Kai'Sa - Daughter of the Void"]:
        errors.append("Kai'Sa must be Rune Generation")
    if "Cost Reduction" not in by_name["Noxus Hopeful"]:
        errors.append("Noxus Hopeful must be Cost Reduction")
    if "Energy Generation" not in by_name["Threshold of the Gray"]:
        errors.append("Threshold of the Gray must be Energy Generation")
    if by_name["Doran's Ring"] or by_name["Cloth Armor"]:
        errors.append("Equip-only cards should have an empty tag list")

    if errors:
        print(f"{len(errors)} tag errors")
        for err in errors[:30]:
            print(" -", err)
        return 1

    print(f"Sample OK: {len(cards)} cards, {len(tags_db)} index keys tagged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
