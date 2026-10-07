---
name: card-tagger
description: Skill for the AI tagger system that explains how to run the automated batch tagging process for new Riftbound cards.
---

# Card Tagger Skill

You are the **Riftbound Card Data Manager**. When the user asks to tag new cards or update the card database tags, use this skill.

## Objective
Every searchable card needs functional tags from `data/db/glossary.json`. That glossary is the only definition of what each tag and each keyword means. `data/db/tag_sample.json` is the calibration set: 100 unique cards already judged. Reprints of those cards carry the same tags in `data/db/card_tags.json`.

Do not invent tag meanings in the prompt. Read the glossary.

## The Automation Script
**Script Path**: `scripts/ai_tagger.py`

### How to use it
1. The full catalog run needs `GEMINI_API_KEY`.
2. See what is left without calling the API:
   ```bash
   python scripts/ai_tagger.py --dry-run
   ```
3. Tag a bounded batch:
   ```bash
   python scripts/ai_tagger.py --limit 100
   ```
4. Tag everything still missing:
   ```bash
   python scripts/ai_tagger.py
   ```

The script loads `card_index.json`, skips Basic and Token cards, skips any card that already has tags, copies tags onto untagged reprints, and sends only the canonical printing of each remaining card to `gemini-3.8-flash` in batches of 25. Results are saved to `data/db/card_tags.json`.

### Tag taxonomy
The live tags and the retired `Ramp` alias are in `data/db/glossary.json`. Do not keep a second list here.

Rules the model must follow are the `tagging_rules` in that file. The important ones: at most one of Aggro, Control, Midrange, Combo; never use Midrange as a default; Rune Generation, Cost Reduction, and Energy Generation are different; Discard is your own cards and Hand Disruption is the opponent's hand.

## Rules
- Do not tag the remaining catalog by hand. Use the script.
- Do not overwrite `tag_sample.json`. Those 100 cards are the standard. The script leaves already tagged cards alone.
- If the script fails because the API key is missing, say that `GEMINI_API_KEY` has to be set. The calibration sample can still be searched without it.
- After a tagging run, check the sample still holds with `python scripts/validate_tags.py`.
