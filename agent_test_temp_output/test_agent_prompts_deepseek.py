import os
import json
from openai import OpenAI
import sys

# Ensure the main aider directory is in the Python path to import prompts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aider import prompts

# --- Configuration ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
MODELS_TO_TEST = ["deepseek-chat", "deepseek-reasoner"] # Add "deepseek-coder" if desired
# MODEL_TO_TEST = "deepseek-chat" # For quicker focused testing

client = None

# --- Sample Data for Prompts ---
sample_task_initial = "Create a Python script that sorts a list of numbers and writes the sorted list to a file."
sample_task_decomposed_parent = "Develop the core sorting module for the number sorting utility."
sample_sub_tasks_for_parent = [
    "Implement quicksort algorithm.",
    "Implement merge sort algorithm.",
    "Add a function to select sorting algorithm based on input size."
]
sample_overall_plan_deliverables = [
    "Define input/output file formats.",
    sample_task_decomposed_parent,
    "Implement file reading and writing operations.",
    "Create command-line interface for the script."
]


# --- Helper Functions ---
def initialize_client():
    global client
    if not DEEPSEEK_API_KEY:
        print("ERROR: DEEPSEEK_API_KEY environment variable not set.")
        exit(1)
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )

def make_api_call(model_name, system_prompt_content, user_prompt_content="", expect_json_object=True):
    if not client:
        print("ERROR: OpenAI client not initialized.")
        return False, "Client not initialized"

    messages = [{"role": "system", "content": system_prompt_content}]
    if user_prompt_content:
        messages.append({"role": "user", "content": user_prompt_content})
    elif model_name == "deepseek-reasoner": # Add dummy user prompt for reasoner if no other user prompt
        messages.append({"role": "user", "content": "Please generate the response based on the system instructions."})

    print(f"    System Prompt for {model_name}:")
    print("```")
    print(system_prompt_content)
    print("```")

    if user_prompt_content:
        print(f"    User Prompt for {model_name}:")
        print("```")
        print(user_prompt_content)
        print("```")

    try:
        response_params = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.1,
        }
        if expect_json_object: # Only add response_format if we expect a JSON object directly from API
            response_params["response_format"] = {'type': 'json_object'}

        response = client.chat.completions.create(**response_params)
        
        raw_content = response.choices[0].message.content
        print(f"    Raw LLM Response from {model_name}:")
        print("```")
        print(raw_content)
        print("```")

        if expect_json_object: # If API was supposed to return JSON
            try:
                parsed_data = json.loads(raw_content) # Still parse, as API guarantees it
                return True, parsed_data
            except json.JSONDecodeError as e:
                print(f"    ERROR: JSONDecodeError despite json_object mode for {model_name}: {e}")
                return False, f"JSONDecodeError: {e}. Raw: {raw_content}"
        else: # If API returned raw string, we try to parse it as JSON
            try:
                parsed_data = json.loads(raw_content)
                return True, parsed_data
            except json.JSONDecodeError as e:
                print(f"    WARN: Could not parse raw string output as JSON for {model_name}: {e}")
                return False, f"Raw string not JSON: {e}. Raw: {raw_content}"

    except Exception as e:
        # Handle specific DeepSeek error for reasoner and JSON mode
        if "does not support Json Output" in str(e) and model_name == "deepseek-reasoner":
            print(f"    INFO: {model_name} does not support json_object mode. Will attempt to parse raw output.")
            # Fall through to re-attempt without json_object if we decide to implement retry logic
            # For now, this error will be caught by the outer logic if expect_json_object was true
            # If expect_json_object was false, this specific error shouldn't happen here.
            # This is more of a safeguard.
            return False, f"API Error (known: reasoner json mode): {e}"

        print(f"    ERROR: API call failed for {model_name}: {e}")
        return False, f"API Error: {e}"

def validate_recursive_decomp_json(data):
    if not isinstance(data, dict):
        return False, "Data is not a dictionary."
    if "is_atomic" not in data or not isinstance(data["is_atomic"], bool):
        return False, "Missing or invalid 'is_atomic' key (must be boolean)."
    if "sub_tasks" not in data or not isinstance(data["sub_tasks"], list):
        return False, "Missing or invalid 'sub_tasks' key (must be a list)."
    if not all(isinstance(item, str) for item in data["sub_tasks"]):
        return False, "Not all items in 'sub_tasks' are strings."
    return True, "Validation successful."

def validate_json_list_of_strings(data, model_name, expect_direct_list=False, list_can_be_empty=False):
    expected_key = "test_list"
    actual_list = None

    if expect_direct_list:
        if not isinstance(data, list):
            return False, f"Data is not a direct list as expected. Model: {model_name}"
        actual_list = data
    else:
        # Expect a dictionary containing the list under expected_key
        if not isinstance(data, dict):
            return False, f"Data is not a dictionary (expected dict with key '{expected_key}'). Model: {model_name}"
        if expected_key not in data:
            return False, f"Data dictionary does not contain the expected key '{expected_key}'. Model: {model_name}"
        
        actual_list = data[expected_key]

    if not isinstance(actual_list, list):
        # This case should ideally be caught by the checks above if structure is wrong
        return False, f"The extracted data is not a list. Model: {model_name}"
    if not list_can_be_empty and not actual_list:
        return False, f"List is empty, but was expected to be non-empty. Model: {model_name}"
    if not all(isinstance(item, str) for item in actual_list):
        return False, f"Not all items in the list are strings. Model: {model_name}"
    return True, "Validation successful."

# --- Test Cases ---

def test_recursive_decomposition(model_name):
    print(f"  [Test Case] Recursive Decomposition Prompt for {model_name}")
    system_prompt = prompts.agent_recursive_decompose_task_system.format(
        task_description=sample_task_initial,
        current_depth=0,
        max_depth=2
    )
    
    use_json_mode = model_name != "deepseek-reasoner"
    success, result = make_api_call(model_name, system_prompt, expect_json_object=use_json_mode)
    
    if success:
        # If not use_json_mode, result is already parsed string if it was JSON, or error
        # If use_json_mode, result is parsed JSON from API
        is_valid, msg = validate_recursive_decomp_json(result)
        if is_valid:
            print(f"    PASS: Recursive decomposition output is valid JSON for {model_name}.")
            print(f"    Result: {json.dumps(result, indent=2)}")
        else:
            print(f"    FAIL: Recursive decomposition JSON validation failed for {model_name}: {msg}")
            print(f"    Received: {json.dumps(result, indent=2) if isinstance(result, (dict, list)) else result}")
    else:
        print(f"    FAIL: API call for recursive decomposition failed for {model_name}: {result}")
    print("-" * 40)

def test_unit_test_generation(model_name):
    print(f"  [Test Case] Unit Test Generation Prompt for {model_name}")
    # The prompt itself now strongly requests a direct JSON list
    system_prompt = prompts.agent_generate_unit_tests_system.format(
        task_description="Implement a Python function `add(a, b)` that returns the sum of a and b."
    )

    # For unit tests, we now expect a direct JSON array from both models, so no json_object mode for chat.
    use_json_mode_for_chat = False 
    success, result = make_api_call(model_name, system_prompt, expect_json_object=use_json_mode_for_chat if model_name == "deepseek-chat" else False)
    
    if success:
        is_valid, msg = validate_json_list_of_strings(result, model_name, expect_direct_list=True, list_can_be_empty=False)
        if is_valid:
            print(f"    PASS: Unit test generation output is valid direct JSON list of strings for {model_name}.")
            print(f"    Result: {json.dumps(result, indent=2)}")
        else:
            print(f"    FAIL: Unit test generation JSON validation failed for {model_name}: {msg}")
            print(f"    Received: {json.dumps(result, indent=2) if isinstance(result, (dict, list)) else result}")
    else:
        print(f"    FAIL: API call for unit test generation failed for {model_name}: {result}")
    print("-" * 40)

def test_integration_tests_major_deliverable(model_name):
    print(f"  [Test Case] Integration Tests (Major Deliverable) Prompt for {model_name}")
    system_prompt = prompts.agent_generate_integration_tests_for_major_deliverable_system.format(
        major_deliverable_description=sample_task_decomposed_parent,
        atomic_sub_task_descriptions_list="\\n".join([f"- {st}" for st in sample_sub_tasks_for_parent])
    )

    use_json_mode = model_name != "deepseek-reasoner"
    success, result = make_api_call(model_name, system_prompt, expect_json_object=use_json_mode)
    
    if success:
        is_valid, msg = validate_json_list_of_strings(result, model_name, expect_direct_list=False, list_can_be_empty=False)
        if is_valid:
            print(f"    PASS: Integration tests (major deliverable) output is valid JSON list for {model_name}.")
            print(f"    Result: {json.dumps(result, indent=2)}")
        else:
            print(f"    FAIL: Integration tests (major deliverable) JSON validation failed for {model_name}: {msg}")
            print(f"    Received: {json.dumps(result, indent=2) if isinstance(result, (dict, list)) else result}")
    else:
        print(f"    FAIL: API call for integration tests (major deliverable) failed for {model_name}: {result}")
    print("-" * 40)

def test_overall_integration_tests(model_name):
    print(f"  [Test Case] Overall Integration Tests Prompt for {model_name}")
    system_prompt = prompts.agent_generate_overall_integration_tests_system.format(
        initial_task_description=sample_task_initial,
        major_deliverables_list_description="\\n".join([f"- {md}" for md in sample_overall_plan_deliverables])
    )
    use_json_mode = model_name != "deepseek-reasoner"
    success, result = make_api_call(model_name, system_prompt, expect_json_object=use_json_mode)
    
    if success:
        is_valid, msg = validate_json_list_of_strings(result, model_name, expect_direct_list=False, list_can_be_empty=False)
        if is_valid:
            print(f"    PASS: Overall integration tests output is valid JSON list for {model_name}.")
            print(f"    Result: {json.dumps(result, indent=2)}")
        else:
            print(f"    FAIL: Overall integration tests JSON validation failed for {model_name}: {msg}")
            print(f"    Received: {json.dumps(result, indent=2) if isinstance(result, (dict, list)) else result}")
    else:
        print(f"    FAIL: API call for overall integration tests failed for {model_name}: {result}")
    print("-" * 40)

# --- Main Execution ---
if __name__ == "__main__":
    initialize_client() # Initialize client once
    if not client:
        exit(1)

    for model in MODELS_TO_TEST:
        print(f"\n{'='*10} Testing Model: {model} {'='*10}")
        test_recursive_decomposition(model)
        test_unit_test_generation(model)
        test_integration_tests_major_deliverable(model)
        test_overall_integration_tests(model)
        print(f"{'='*10} Finished Testing Model: {model} {'='*10}\n")

    print("All prompt tests completed.") 