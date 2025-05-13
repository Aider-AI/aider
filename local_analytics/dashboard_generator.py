import json
import os
from datetime import datetime
from pathlib import Path
import html
from collections import defaultdict # Import defaultdict
import webbrowser





# Define file paths (assuming they are in the same directory as the script)
BASE_DIR = Path(__file__).resolve().parent
SESSION_DATA_FILE = BASE_DIR / "session.jsonl"
COLOR_CLASSES = ["teal", "green", "yellow", "red"] # For dynamic history item colors
DASHBOARD_TEMPLATE_FILE = BASE_DIR / "dashboard.html"
DASHBOARD_OUTPUT_FILE = BASE_DIR / "dashboard_generated.html"

def format_timestamp(ts_str):
    """Formats an ISO timestamp string into a more readable format."""
    if not ts_str:
        return "N/A"
    try:
        # Handle potential 'Z' for UTC
        if ts_str.endswith('Z'):
            ts_str = ts_str[:-1] + '+00:00'
        dt_obj = datetime.fromisoformat(ts_str)
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts_str # Return original if parsing fails

def format_duration(seconds):
    """Formats a duration in seconds into a human-readable string (e.g., 1m 38s)."""
    if seconds is None:
        return "N/A"
    try:
        s = int(seconds)
        if s < 0:
            return "N/A"
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"
    except (ValueError, TypeError):
        return "N/A"

def escape_html(text):
    """Escapes HTML special characters in a string."""
    if text is None:
        return ""
    return html.escape(str(text))

def read_session_data(filepath):
    """Reads session data from a JSONL file."""
    data = []
    if not filepath.exists():
        print(f"Error: Session data file not found at {filepath}")
        return data
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from line: {line.strip()} - {e}")
    return data

def calculate_cost_by_model(all_data):
    """
    Calculates the total estimated cost per model from all session data.
    """
    cost_by_model = defaultdict(float)
    if not all_data:
        return dict(cost_by_model)

    for data in all_data:
        # Iterate through the models used summary for this interaction
        models_summary = data.get("models_used_summary", [])
        if not isinstance(models_summary, list):
             # print(f"Warning: 'models_used_summary' is not a list in data: {data}") # Optional debug
             continue

        for model_info in models_summary:
            if not isinstance(model_info, dict):
                # print(f"Warning: Item in 'models_used_summary' is not a dict in data: {data}") # Optional debug
                continue

            model_name = model_info.get("name", "Unknown Model")
            cost = model_info.get("cost", 0.0)

            # Ensure cost is a number before adding
            if isinstance(cost, (int, float)):
                cost_by_model[model_name] += cost
            else:
                print(f"Warning: Found non-numeric cost value for model '{model_name}': {cost} in data: {data}")

    return dict(cost_by_model) # Convert defaultdict to dict for final return

def format_cost_by_model_html(cost_by_model):
    """Generates HTML list for cost breakdown by model."""
    if not cost_by_model:
        return "<ul><li>No model cost data available.</li></ul>"

    # Sort models by cost descending
    sorted_models = sorted(cost_by_model.items(), key=lambda item: item[1], reverse=True)

    list_items_html = ""
    for model, cost in sorted_models:
        list_items_html += f"""
        <li>
            <span class="model-name">{escape_html(model)}:</span>
            <span class="model-cost">${cost:.4f}</span>
        </li>
        """
    return f"<ul>{list_items_html}</ul>"


def generate_stats_overview_html(all_data, cost_by_model):
    """Generates HTML for the main stats overview section (Total Cost + Cost by Model)."""
    total_estimated_cost = sum(item.get("token_summary", {}).get("estimated_cost", 0.0) or 0.0 for item in all_data)

    last_entry_timestamp_str = "N/A"
    if all_data:
        # Assuming all_data is sorted with newest entry last after reading
        last_interaction_data = all_data[-1] # Newest interaction
        last_entry_timestamp_str = format_timestamp(last_interaction_data.get("interaction_timestamp"))

    model_cost_list_html = format_cost_by_model_html(cost_by_model)

    return f"""
      <div class="main-stat-item">
        <div class="stat-number-main">${total_estimated_cost:.4f}</div>
        <div class="stat-label">TOTAL ESTIMATED COST</div>
        <div class="last-entry">
          <span class="data-label">Last Entry:</span>
          <span class="data-value">{escape_html(last_entry_timestamp_str)}</span>
        </div>
      </div>
      <div class="model-cost-summary-box">
        <h3>COST BY MODEL</h3>
        {model_cost_list_html}
      </div>
      """

def generate_secondary_stats_html(all_data):
    """Generates HTML for the secondary stats section (Tokens, Duration, Sessions)."""
    if not all_data:
        # Return the structure with N/A values if no data, matching dashboard.html's expectation
        return """
        <div class="right-stats-group">
            <div class="stat-box">
              <div class="stat-number-medium">0</div>
              <div class="stat-label">TOTAL PROMPT TOKENS</div>
            </div>
            <div class="stat-box">
              <div class="stat-number-medium">0s</div>
              <div class="stat-label">TOTAL INTERACTION DURATION</div>
            </div>
            <div class="stat-box">
              <div class="stat-number-medium">0</div>
              <div class="stat-label">TOTAL COMPLETION TOKENS</div>
            </div>
            <div class="stat-box">
              <div class="stat-number-medium">0</div>
              <div class="stat-label">TOTAL SESSIONS</div>
            </div>
          </div>"""

    total_duration_seconds = sum(item.get("interaction_duration_seconds", 0) or 0 for item in all_data)
    total_prompt_tokens = sum(item.get("token_summary", {}).get("prompt_tokens", 0) or 0 for item in all_data)
    total_completion_tokens = sum(item.get("token_summary", {}).get("completion_tokens", 0) or 0 for item in all_data)

    total_sessions = 0
    if all_data:
        session_ids = set()
        for item in all_data:
            if item.get("session_id"):
                session_ids.add(item.get("session_id"))
        total_sessions = len(session_ids)

    formatted_duration = format_duration(total_duration_seconds)
    formatted_prompt_tokens = f"{total_prompt_tokens / 1_000_000:.2f}M" if total_prompt_tokens >= 1_000_000 else str(total_prompt_tokens)
    formatted_completion_tokens = f"{total_completion_tokens / 1_000_000:.2f}M" if total_completion_tokens >= 1_000_000 else str(total_completion_tokens)

    return f"""
      <div class="right-stats-group">
        <div class="stat-box">
          <div class="stat-number-medium">{formatted_prompt_tokens}</div>
          <div class="stat-label">TOTAL PROMPT TOKENS</div>
        </div>
        <div class="stat-box">
          <div class="stat-number-medium">{formatted_duration}</div>
          <div class="stat-label">TOTAL INTERACTION DURATION</div>
        </div>
        <div class="stat-box">
          <div class="stat-number-medium">{formatted_completion_tokens}</div>
          <div class="stat-label">TOTAL COMPLETION TOKENS</div>
        </div>
        <div class="stat-box">
          <div class="stat-number-medium">{total_sessions}</div>
          <div class="stat-label">TOTAL SESSIONS</div>
        </div>
      </div>"""


def generate_collapsible_list_html(title, items_list):
    items_list = items_list or [] # Ensure items_list is not None
    if not items_list:
        return f"<p><strong>{escape_html(title)}:</strong> None</p>"

    list_items_html = "".join(f"<li>{escape_html(item)}</li>" for item in items_list)
    return f"""
    <details class="collapsible-section">
        <summary class="collapsible-summary">{escape_html(title)} ({len(items_list)})</summary>
        <div class="collapsible-content">
            <ul>{list_items_html}</ul>
        </div>
    </details>
    """

def generate_token_summary_html(token_summary):
    token_summary = token_summary or {} # Ensure token_summary is not None
    if not token_summary:
        return "<p>No token summary available.</p>"

    return f"""
    <details class="collapsible-section">
        <summary class="collapsible-summary">Token Summary</summary>
        <div class="collapsible-content">
            <p><strong>Prompt Tokens:</strong> {token_summary.get("prompt_tokens", "N/A")}</p>
            <p><strong>Completion Tokens:</strong> {token_summary.get("completion_tokens", "N/A")}</p>
            <p><strong>Total Tokens:</strong> {token_summary.get("total_tokens", "N/A")}</p>
            <p><strong>Estimated Cost:</strong> ${token_summary.get("estimated_cost", 0.0):.6f}</p>
        </div>
    </details>
    """

def generate_models_used_summary_html(models_summary):
    models_summary = models_summary or [] # Ensure models_summary is not None
    if not models_summary:
        return "<p>No models used summary available.</p>"

    rows_html = ""
    for model_info in models_summary:
        model_info = model_info or {} # Ensure model_info is not None
        rows_html += f"""
        <tr>
            <td>{escape_html(model_info.get("name"))}</td>
            <td>{model_info.get("calls", "N/A")}</td>
            <td>${model_info.get("cost", 0.0):.6f}</td>
            <td>{model_info.get("prompt_tokens", "N/A")}</td>
            <td>{model_info.get("completion_tokens", "N/A")}</td>
        </tr>
        """

    return f"""
    <details class="collapsible-section">
        <summary class="collapsible-summary">Models Used Summary ({len(models_summary)})</summary>
        <div class="collapsible-content">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Calls</th>
                        <th>Cost</th>
                        <th>Prompt Tokens</th>
                        <th>Completion Tokens</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </details>
    """

def generate_llm_calls_details_html(llm_calls):
    llm_calls = llm_calls or [] # Ensure llm_calls is not None
    if not llm_calls:
        return "<p>No LLM call details available.</p>"

    rows_html = ""
    for call in llm_calls:
        call = call or {} # Ensure call is not None
        rows_html += f"""
        <tr>
            <td>{escape_html(call.get("model"))}</td>
            <td>{escape_html(call.get("id"))}</td>
            <td>{escape_html(call.get("finish_reason", "N/A"))}</td>
            <td>{call.get("prompt_tokens", "N/A")}</td>
            <td>{call.get("completion_tokens", "N/A")}</td>
            <td>${call.get("cost", 0.0):.6f}</td>
            <td>{format_timestamp(call.get("timestamp"))}</td>
        </tr>
        """

    return f"""
    <details class="collapsible-section">
        <summary class="collapsible-summary">LLM Calls Details ({len(llm_calls)})</summary>
        <div class="collapsible-content">
            <table>
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>ID</th>
                        <th>Finish Reason</th>
                        <th>Prompt Tokens</th>
                        <th>Completion Tokens</th>
                        <th>Cost</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </details>
    """

def generate_interaction_html(interaction_data, index, use_special_color_bar=False, special_color_class="blue"):
    """Generates HTML for a single interaction entry."""
    interaction_data = interaction_data or {}
    session_id = escape_html(interaction_data.get("session_id", f"interaction-{index}"))
    project_name = escape_html(interaction_data.get("project_name", "N/A"))
    timestamp_str = format_timestamp(interaction_data.get("interaction_timestamp"))
    duration_str = format_duration(interaction_data.get("interaction_duration_seconds"))
    query_text = escape_html(interaction_data.get("query", "No query provided."))
    aider_version = escape_html(interaction_data.get("aider_version", "N/A"))
    platform_info = escape_html(interaction_data.get("platform_info", "N/A"))
    python_version = escape_html(interaction_data.get("python_version", "N/A"))

    if use_special_color_bar:
        color_bar_class = special_color_class
    else:
        if COLOR_CLASSES: # Ensure COLOR_CLASSES is not empty
            color_bar_class = COLOR_CLASSES[index % len(COLOR_CLASSES)]
        else:
            color_bar_class = "teal" # Fallback if COLOR_CLASSES is somehow empty
    return f"""
    <div class="history-item" id="interaction-{session_id}-{index}">
      <div class="color-bar {color_bar_class}"></div>
      <div class="item-content">
        <div class="item-header">
          <h3>{project_name}</h3> 
          <span class="timestamp">{timestamp_str} (Duration: {duration_str})</span>
        </div>
        <p class="entry-text">
          <span class="data-label">Query:</span>
          <span class="data-value">{query_text}</span>
        </p>
        <div class="details">
          <dl>
            <dt class="data-label">Session ID:</dt>
            <dd class="data-value">{session_id}</dd>

            <dt class="data-label">Aider Version:</dt>
            <dd class="data-value">
              {aider_version}
              <span class="data-label">Platform:</span>
              <span class="data-value">{platform_info}</span>,
              <span class="data-label">Python:</span>
              <span class="data-value">{python_version}</span>
            </dd>

            <dt class="data-label">Token Usage:</dt>
            <dd class="data-value">{generate_token_summary_html(interaction_data.get("token_summary"))}</dd>

            <dt class="data-label">Models Used:</dt>
            <dd class="data-value">{generate_models_used_summary_html(interaction_data.get("models_used_summary"))}</dd>

            <dt class="data-label">LLM Call Details:</dt>
            <dd class="data-value">{generate_llm_calls_details_html(interaction_data.get("llm_calls_details"))}</dd>

            <dt class="data-label">Modified Files (in chat context):</dt>
            <dd class="data-value">{generate_collapsible_list_html("Modified Files in Chat", interaction_data.get("modified_files_in_chat"))}</dd>

            <dt class="data-label">Commits Made This Interaction:</dt>
            <dd class="data-value">{generate_collapsible_list_html("Commits Made This Interaction", interaction_data.get("commits_made_this_interaction"))}</dd>
          </dl>
        </div>
      </div>
    </div>
    """

def main():
    """Main function to generate the dashboard."""
    all_session_data = read_session_data(SESSION_DATA_FILE)

    # Calculate cost by model once
    cost_by_model = calculate_cost_by_model(all_session_data)

    # Generate HTML for the different sections
    stats_overview_html = generate_stats_overview_html(all_session_data, cost_by_model)
    secondary_stats_html = generate_secondary_stats_html(all_session_data)

    latest_interaction_display_html = ""
    history_entries_html = ""
    project_name_header = "AIDER ANALYTICS" # Default if no data

    if not all_session_data:
        latest_interaction_display_html = '<p class="empty-state">No latest interaction data to display.</p>'
        history_entries_html = '<p class="empty-state">No interaction history to display.</p>'
    else:
        # Data is assumed to be oldest to newest from read_session_data
        data_for_processing = list(all_session_data) # Make a copy

        latest_interaction_data = data_for_processing.pop() # Removes and returns the last item (newest)
        project_name_header = escape_html(latest_interaction_data.get("project_name", "AIDER ANALYTICS")) # Get project name from latest interaction

        # Index 0 for latest, but color is overridden by use_special_color_bar
        latest_interaction_display_html = generate_interaction_html(latest_interaction_data, 0, use_special_color_bar=True, special_color_class="blue")

        history_entries_html_parts = []
        if not data_for_processing:
            history_entries_html = '<p class="empty-state">No further interaction history to display.</p>'
        else:
            # Iterate from newest to oldest for display for the rest of the history
            for i, interaction_data in enumerate(reversed(data_for_processing)):
                # i will be 0 for the newest in remaining, 1 for next, etc.
                history_entries_html_parts.append(generate_interaction_html(interaction_data, i))
            history_entries_html = "\n".join(history_entries_html_parts)
            if not history_entries_html_parts: # Should not happen if data_for_processing was not empty
                 history_entries_html = '<p class="empty-state">No further interaction history to display.</p>'


    if not DASHBOARD_TEMPLATE_FILE.exists():
        print(f"Error: Dashboard template file not found at {DASHBOARD_TEMPLATE_FILE}")
        # Create a basic HTML structure if template is missing, to show some output
        output_content = f"""
        <html>
            <head><title>Aider Analytics Dashboard</title></head>
            <body>
                <h1>{project_name_header} - Aider Analytics Dashboard</h1>
                <h2>Stats Overview</h2>
                <section class="stats-overview">{stats_overview_html}</section>
                <h2>Secondary Stats</h2>
                <section class="secondary-stats-section">{secondary_stats_html}</section>
                <h2>Latest Interaction</h2>
                <section class="latest-interaction-display">{latest_interaction_display_html}</section>
                <h2>Interaction History</h2>
                <section class="text-entry-history-section">{history_entries_html}</section>
                <p><small>Note: dashboard.html template was not found. This is a fallback display.</small></p>
            </body>
        </html>
        """
    else:
        with open(DASHBOARD_TEMPLATE_FILE, "r", encoding="utf-8") as f:
            template_content = f.read()

        output_content = template_content.replace("<!-- AIDER_ANALYTICS_PROJECT_NAME -->", project_name_header)
        output_content = output_content.replace("<!-- AIDER_ANALYTICS_STATS_OVERVIEW_CONTENT -->", stats_overview_html)
        output_content = output_content.replace("<!-- AIDER_ANALYTICS_SECONDARY_STATS_CONTENT -->", secondary_stats_html)
        output_content = output_content.replace("<!-- AIDER_ANALYTICS_LATEST_INTERACTION_CONTENT -->", latest_interaction_display_html)
        output_content = output_content.replace("<!-- AIDER_ANALYTICS_HISTORY_ENTRIES_CONTENT -->", history_entries_html)

        # Check if placeholders were correctly replaced (optional, for debugging)
        # if "<!-- AIDER_ANALYTICS_STATS_OVERVIEW_CONTENT -->" in output_content and "<!-- AIDER_ANALYTICS_STATS_OVERVIEW_CONTENT -->" not in stats_overview_html:
        #     print("Warning: Stats overview placeholder was not replaced.")
        # if "<!-- AIDER_ANALYTICS_SECONDARY_STATS_CONTENT -->" in output_content and "<!-- AIDER_ANALYTICS_SECONDARY_STATS_CONTENT -->" not in secondary_stats_html:
        #     print("Warning: Secondary stats placeholder was not replaced.")
        # if "<!-- AIDER_ANALYTICS_LATEST_INTERACTION_CONTENT -->" in output_content and "<!-- AIDER_ANALYTICS_LATEST_INTERACTION_CONTENT -->" not in latest_interaction_display_html:
        #     print("Warning: Latest interaction placeholder was not replaced.")
        # if "<!-- AIDER_ANALYTICS_HISTORY_ENTRIES_CONTENT -->" in output_content and "<!-- AIDER_ANALYTICS_HISTORY_ENTRIES_CONTENT -->" not in history_entries_html:
        #     print("Warning: History entries placeholder was not replaced.")


    with open(DASHBOARD_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"Dashboard generated: {DASHBOARD_OUTPUT_FILE.resolve().as_uri()}")
    webbrowser.open(DASHBOARD_OUTPUT_FILE.resolve().as_uri())


if __name__ == "__main__":
    main()
