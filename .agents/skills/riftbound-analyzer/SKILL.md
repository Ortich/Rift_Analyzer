---
name: riftbound-analyzer
description: Expert AI interpretation of Riftbound deck analysis pipeline outputs. Automatically executes the simulator and provides strategic feedback.
---

# Riftbound Analyzer Skill

This skill is retired. Deck review is tag search plus the deck JSON, using the `deck-consultant` skill. Do not run `scripts/analyze_pipeline.py` and do not report simulated win rates.

The sections below describe the old mathematical pipeline. Leave them unused.

## Execution Flow
When a user asks to analyze or improve a deck, follow the `deck-consultant` skill. Search `data/db/card_tags.json` with `scripts/search_cards.py` and read `data/db/glossary.json`. Do not execute the simulator.

## Understanding the Data
- `parsed_deck.json`: Contains the static breakdown (Types, Domains, Energy Curve). Keep in mind Champions and Legends sit in Special Zones and do not count towards the 40-card main deck.
- `final_report.json`: Contains the Viktor's Deck Simulation results, specifically the mathematical Win Rates against 3 archetypes (Aggro, Control, Midrange), plus the overall Power Level (0-10) and Tier. 

## Output Template
You must strictly follow this 4-part markdown structure when responding to the user.

### 1. 📊 Resumen Ejecutivo
- State the **Power Level** and **Tier**.
- Validate the deck (Is it exactly 40 cards in the main deck? Does it use max 2 domains?).
- Provide a 1-2 sentence high-level summary of the deck's identity.

### 2. ⚔️ Matchup Spread (Simulaciones PvP)
- Display the Win Rates against Aggro, Control, and Midrange.
- Use a markdown table to present these stats clearly.

### 3. 🔍 Diagnóstico del Mazo
- **Energy Curve Chart**: Use markdown block characters (e.g., `█`, `▆`, `▃`, `_`) to draw a visual bar chart of the Energy Curve (Cost 0, 1, 2, 3, 4, 5+).
- Diagnose the biggest weakness based on the Win Rates. Why is it losing to a specific bot? (e.g., Lacks early presence vs Aggro, Lacks removal for big bombs vs Midrange, Lacks resilience vs Control).
- Evaluate the Interaction score (Spells). Does it have enough combat tricks or direct damage to win lanes?

### 4. 🛠️ Propuestas de Mejora (IN / OUT)
- Recommend specific, actionable Structural Substitutions. 
- Format as explicit **[OUT]** (cards to remove) and **[IN]** (what type of cards to add, e.g., "Add low-cost units with Assault", "Add fast removal").
- Always remind the user that the main deck must remain exactly 40 cards.

## Tone
Professional, analytical, and highly tactical. You are a coach trying to help the player reach the competitive tiers.
