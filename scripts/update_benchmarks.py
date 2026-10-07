import sys
import os
import json
import glob

# Ensure the core/scripts modules are accessible
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.analyze_deck as analyze_deck
import core.simulator as simulator

def update_benchmarks():
    benchmarks_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "benchmarks")
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "db")
    benchmarks_file = os.path.join(db_dir, "benchmarks.json")
    
    deck_files = glob.glob(os.path.join(benchmarks_dir, "*.json"))
    
    archetype_data = {}
    
    for df in deck_files:
        print(f"Benchmarking {df}...")
        with open(df, "r", encoding="utf-8") as f:
            meta = json.load(f)
            archetype = meta.get("archetype", "Unknown")
            
        # Parse it
        parsed = analyze_deck.analyze_deck(df)
        if not parsed:
            continue
            
        # Run Simulator (reduce iterations slightly for benchmarks, or keep at 1000)
        parsed_path = os.path.join(db_dir, "parsed_deck.json")
        results = simulator.run_pvp_simulation(parsed_path, iterations=1000)
        
        if results:
            avg_wr = results.get("average_win_rate", 0)
            if archetype not in archetype_data:
                archetype_data[archetype] = []
            archetype_data[archetype].append(avg_wr)
            
    final_benchmarks = {}
    for arch, wrs in archetype_data.items():
        avg = sum(wrs) / len(wrs)
        final_benchmarks[arch] = {
            "expected_win_rate": round(avg, 2),
            "samples": len(wrs)
        }
        
    with open(benchmarks_file, "w", encoding="utf-8") as f:
        json.dump(final_benchmarks, f, indent=2)
        
    print(f"\nBenchmarks updated successfully: {json.dumps(final_benchmarks, indent=2)}")

if __name__ == "__main__":
    update_benchmarks()
