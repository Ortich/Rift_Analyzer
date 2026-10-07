"""Filter the local card index by functional tags."""

import argparse
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB = os.path.join(ROOT, "data", "db")


def base_name(name):
    name = re.sub(r"\s*\([^)]*\)\s*", " ", name or "").strip()
    return re.sub(r"\s+", " ", name).lower()


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def deck_counts(path):
    if not path:
        return {}
    deck = load(path)
    counts = {}
    for name, qty in (deck.get("main_deck") or {}).items():
        counts[base_name(name)] = counts.get(base_name(name), 0) + int(qty)
    for field in ("champion", "legend"):
        if deck.get(field):
            counts[base_name(deck[field])] = counts.get(base_name(deck[field]), 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser(description="Search tagged Riftbound cards.")
    parser.add_argument("--tags", required=True, help="Comma-separated tags. A card must have all of them.")
    parser.add_argument("--domains", default="", help="Comma-separated domains. A card must use only these.")
    parser.add_argument("--max-energy", type=int, default=None)
    parser.add_argument("--deck", default="", help="Deck JSON. Skip cards already at 3 copies.")
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()

    wanted = [part.strip() for part in args.tags.split(",") if part.strip()]
    domains = {part.strip() for part in args.domains.split(",") if part.strip()}
    glossary = load(os.path.join(DB, "glossary.json"))
    legal = set(glossary["tags"])
    unknown = [tag for tag in wanted if tag not in legal]
    if unknown:
        print(f"Unknown tags: {', '.join(unknown)}", file=sys.stderr)
        return 1

    index = load(os.path.join(DB, "card_index.json"))["cards"]
    tags_db = load(os.path.join(DB, "card_tags.json"))
    ramp_maps_to = set(glossary["tags"]["Ramp"]["replaced_by"])
    owned = deck_counts(args.deck)

    seen = set()
    hits = []
    for card in index.values():
        name = card.get("name") or ""
        base = base_name(name)
        if base in seen:
            continue
        if card.get("supertype") in ("Basic", "Token"):
            continue
        tags = tags_db.get(name.lower())
        if tags is None:
            tags = tags_db.get(base)
        if not tags:
            continue
        effective = set(tags)
        if "Ramp" in effective:
            effective |= ramp_maps_to
        if not set(wanted).issubset(effective):
            continue
        card_domains = set(card.get("domains") or [])
        if domains and not card_domains <= domains | {"Colorless"}:
            continue
        energy = card.get("energy")
        if args.max_energy is not None and energy is not None and energy > args.max_energy:
            continue
        if owned.get(base, 0) >= 3:
            continue
        seen.add(base)
        hits.append(card)

    hits.sort(key=lambda card: (card.get("energy") is None, card.get("energy") or 0, card.get("name") or ""))
    shown = hits[: args.limit]
    print(f"{len(hits)} cards. Showing {len(shown)}.")
    for card in shown:
        energy = card.get("energy")
        cost = "Legend/Battlefield" if energy is None else f"{energy} Energy"
        domain = ", ".join(card.get("domains") or [])
        tags = tags_db.get((card.get("name") or "").lower(), [])
        print(f"\n{card.get('name')} — {cost} — {domain} — {card.get('type')}")
        print(f"  tags: {', '.join(tags) if tags else '(none)'}")
        text = (card.get("oracle_text") or "").replace("\n", " ")
        print(f"  {text[:280]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
