import json
from pathlib import Path
from collections import defaultdict

def calculate_cost_by_model(filepath):
    """
    Reads session data from a JSONL file and calculates the total estimated cost per model.
    """
    cost_by_model = defaultdict(float)
    if not filepath.exists():
        print(f"Error: Session data file not found at {filepath}")
        return dict(cost_by_model) # Return empty dict if file not found

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                # Iterate through the models used summary for this interaction
                models_summary = data.get("models_used_summary", [])
                if not isinstance(models_summary, list):
                     print(f"Warning: 'models_used_summary' is not a list in line: {line.strip()}")
                     continue

                for model_info in models_summary:
                    if not isinstance(model_info, dict):
                        print(f"Warning: Item in 'models_used_summary' is not a dict in line: {line.strip()}")
                        continue

                    model_name = model_info.get("name", "Unknown Model")
                    cost = model_info.get("cost", 0.0)

                    # Ensure cost is a number before adding
                    if isinstance(cost, (int, float)):
                        cost_by_model[model_name] += cost
                    else:
                        print(f"Warning: Found non-numeric cost value for model '{model_name}': {cost} in line: {line.strip()}")

            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from line: {line.strip()} - {e}")
            except Exception as e:
                print(f"An unexpected error occurred processing line: {line.strip()} - {e}")

    return dict(cost_by_model) # Convert defaultdict to dict for final return

if __name__ == "__main__":
    # Define the path to the session data file
    BASE_DIR = Path(__file__).resolve().parent
    SESSION_DATA_FILE = BASE_DIR / "session.jsonl"

    cost_by_model = calculate_cost_by_model(SESSION_DATA_FILE)

    print("Total Estimated Cost by Model:")
    if cost_by_model:
        # Sort models by cost descending
        sorted_models = sorted(cost_by_model.items(), key=lambda item: item[1], reverse=True)
        for model, cost in sorted_models:
            print(f"  {model}: ${cost:.4f}")
        
        total_overall_cost = sum(cost_by_model.values())
        print("-" * 30)
        print(f"Total Estimated Cost (Overall): ${total_overall_cost:.4f}")
    else:
        print("  No cost data found.")
