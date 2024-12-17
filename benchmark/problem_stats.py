#!/usr/bin/env python

import yaml
from pathlib import Path
from collections import defaultdict
import json

def load_results(dirname):
    """Load all result files from a benchmark directory"""
    dirname = Path(dirname)
    benchmark_dir = Path("tmp.benchmarks") / dirname
    if not benchmark_dir.exists():
        return None
    
    all_results = []
    for fname in benchmark_dir.glob("*/.aider.results.json"):
        try:
            results = json.loads(fname.read_text())
            all_results.append(results)
        except json.JSONDecodeError:
            print(f"Failed to parse {fname}")
            continue
    return all_results

def analyze_exercise_solutions():
    # Load the leaderboard data
    with open("aider/website/_data/edit_leaderboard.yml") as f:
        leaderboard = yaml.safe_load(f)
    
    # Track which models solved each exercise
    exercise_solutions = defaultdict(list)
    
    for entry in leaderboard:
        dirname = entry["dirname"]
        model = entry["model"]
        
        results = load_results(dirname)
        if not results:
            print(f"Could not load results for {dirname}")
            continue
            
        for result in results:
            testcase = result.get("testcase")
            if not testcase:
                continue
                
            # Consider it solved if the last test attempt passed
            tests_outcomes = result.get("tests_outcomes", [])
            if tests_outcomes and tests_outcomes[-1]:
                exercise_solutions[testcase].append(model)
    
    # Print statistics
    print("\nExercise Solution Statistics:")
    print("-" * 40)
    
    # Sort by number of models that solved each exercise
    sorted_exercises = sorted(
        exercise_solutions.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    for testcase, models in sorted_exercises:
        print(f"{testcase}: solved by {len(models)} models")
        #print(f"  Models: {', '.join(models)}")
    
    print("\nSummary:")
    print(f"Total exercises solved at least once: {len(exercise_solutions)}")
    never_solved = 133 - len(exercise_solutions)
    print(f"Never solved by any model: {never_solved}")
    
    # Distribution of solutions
    solved_by_counts = defaultdict(int)
    for models in exercise_solutions.values():
        solved_by_counts[len(models)] += 1
    
    print("\nDistribution of solutions:")
    for count in sorted(solved_by_counts.keys()):
        print(f"Solved by {count} models: {solved_by_counts[count]} exercises")

if __name__ == "__main__":
    analyze_exercise_solutions()
