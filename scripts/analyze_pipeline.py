import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scripts.analyze_deck as analyze_deck
import core.simulator as simulator
import core.score as score

def run_pipeline(deck_file):
    print(f"=== Riftbound Analyzer Pipeline ===")
    print(f"Target Deck: {deck_file}\n")
    
    # Phase 1: Parse and Bucket
    print("--- Phase 1: Parsing & Heuristics ---")
    parsed_data = analyze_deck.analyze_deck(deck_file)
    if not parsed_data:
        print("Pipeline aborted at Phase 1.")
        return
        
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "db")
    parsed_json_path = os.path.join(db_dir, "parsed_deck.json")
    
    print()
    
    # Phase 2: Viktor's Deck Simulation
    print("--- Phase 2: Viktor's Deck Simulation ---")
    sim_results = simulator.run_pvp_simulation(parsed_json_path)
    if not sim_results:
        print("Pipeline aborted at Phase 2.")
        return
        
    print()
    
    import json
    archetype = "Unknown"
    if deck_file.endswith('.json'):
        with open(deck_file, 'r', encoding='utf-8') as f:
            d = json.load(f)
            if 'metadata' in d:
                archetype = d['metadata'].get('archetype', 'Unknown')
            else:
                archetype = d.get('archetype', 'Unknown')
                
    # Phase 3: Scoring & Bracketing
    print("--- Phase 3: Scoring & Bracketing ---")
    score_report = score.generate_score(parsed_json_path, sim_results, deck_archetype=archetype)
    
    print("\nPipeline execution finished successfully.")
    print("Phase 4 (Expert Interpretation) is ready to be triggered via AI.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full Riftbound analysis pipeline.")
    parser.add_argument("deck_file", help="Path to the decklist text file.")
    args = parser.parse_args()
    
    run_pipeline(args.deck_file)
