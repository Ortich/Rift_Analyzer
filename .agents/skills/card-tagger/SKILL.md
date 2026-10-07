---
name: card-tagger
description: Skill for the AI tagger system that explains how to run the automated batch tagging process for new Riftbound cards.
---

# Card Tagger Skill

You are the **Riftbound Card Data Manager**. When the user asks to tag new cards or update the card database tags, use this skill.

## Objective
We have transitioned from a mathematical PvP simulator to a Semantic/Tagging system. To make cards searchable and filterable for the Deckbuilding Consultant, every card in the database needs a list of functional gameplay tags (e.g. `Removal`, `Card Draw`, `Finisher`).

## The Automation Script
We have a Python script that uses the Gemini API to perform batch tagging via Structured Output. 

**Script Path**: `c:\workspace\Rift_Analyzer\scripts\ai_tagger.py`

### How to use it:
1. Ensure the user has the `GEMINI_API_KEY` environment variable set.
2. Run the script using your `run_command` tool:
   ```bash
   python scripts/ai_tagger.py
   ```
3. The script will automatically:
   - Load the `card_index.json`.
   - Identify any cards that aren't yet in `card_tags.json`.
   - Bundle them into batches of 25.
   - Call the `gemini-3.8-flash` API to assign tags.
   - Save the results iteratively to `data/db/card_tags.json`.

### Tag Taxonomy
If the user asks what tags are supported, you can list these:
- Removal, AoE, Card Draw, Ramp, Finisher, Heal/Shield, Combat Trick, Value Engine, Token Generator, Hand Disruption, Trash Synergy, Aggro, Control, Midrange, Combo, Discard, Direct Damage.

## Rules
- DO NOT attempt to tag the cards manually in the chat window. There are hundreds of cards; it costs too many tokens and would hit rate limits or context limits. Always use the script.
- If the script fails because the API key is missing, tell the user they need to set `GEMINI_API_KEY`.
