import json
import os

def generate_score(parsed_deck_path, sim_results, deck_archetype="Unknown"):
    if not os.path.exists(parsed_deck_path):
        print(f"Error: Parsed deck file '{parsed_deck_path}' not found.")
        return None
        
    with open(parsed_deck_path, "r", encoding="utf-8") as f:
        deck_data = json.load(f)
        
    print("--- Scoring & Bracketing ---")
    
    wr_aggro = sim_results.get("Aggro", 50)
    wr_control = sim_results.get("Control", 50)
    wr_midrange = sim_results.get("Midrange", 50)
    avg_wr = sim_results.get("average_win_rate", 50)
    
    # Read Benchmarks
    benchmarks_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "db", "benchmarks.json")
    benchmark_baseline = 50.0
    
    if os.path.exists(benchmarks_path):
        with open(benchmarks_path, "r", encoding="utf-8") as f:
            benchmarks = json.load(f)
            
        # Try to find a benchmark for this archetype, fallback to any archetype's max benchmark
        if deck_archetype in benchmarks:
            benchmark_baseline = benchmarks[deck_archetype].get("expected_win_rate", 50.0)
        else:
            # If archetype not found, use the global average of benchmarks
            if benchmarks:
                benchmark_baseline = sum([b.get("expected_win_rate", 50.0) for b in benchmarks.values()]) / len(benchmarks)
                
    # Safeguard to prevent division by zero or extremely low baselines inflating scores infinitely
    benchmark_baseline = max(0.1, benchmark_baseline)
    
    # Calculate Power Level (0-10 scale based on relative Win Rate)
    # If avg_wr == benchmark_baseline, Power Level = 8.5 (Tier 1 threshold)
    # If avg_wr is 0, Power Level = 1.0
    
    ratio = avg_wr / benchmark_baseline
    power_level = 1.0 + (ratio * 7.5) # 8.5 at 1.0 ratio
    power_level = round(max(1.0, min(10.0, power_level)), 2)
    
    # Bracketing logic (1.0 to 10.0 scale)
    if power_level >= 8.5:
        tier = "Tier 1 (Competitive)"
    elif power_level >= 7.0:
        tier = "Tier 2 (Optimized)"
    elif power_level >= 5.0:
        tier = "Tier 3 (Mid Power)"
    else:
        tier = "Tier 4 (Casual)"
        
    spells_count = deck_data.get("type_breakdown", {}).get("Spells", 0)
    interaction_score = min(10.0, (spells_count / 10.0) * 10)
        
    report = {
        "deck_size": deck_data.get("deck_size"),
        "valid_format": deck_data.get("valid_format"),
        "simulation_results": sim_results,
        "benchmark_baseline_used": benchmark_baseline,
        "scores": {
            "win_rate_vs_aggro": wr_aggro,
            "win_rate_vs_control": wr_control,
            "win_rate_vs_midrange": wr_midrange,
            "interaction": round(interaction_score, 2)
        },
        "power_level": power_level,
        "tier": tier
    }
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "db", "final_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"Final Power Level: {power_level}/10.0 ({tier})")
    print(f"Saved final report to {output_path}\n")
    return report
