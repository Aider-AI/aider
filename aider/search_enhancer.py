import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Any

# Assuming aider.llm.LLM is the class for LLM interactions
# This might need adjustment based on actual LLM class structure in aider
# from aider.llm import LLM

class SearchEnhancer:
    def __init__(self, llm, io): # llm: Model, io: InputOutput
        self.llm = llm
        self.io = io

    def _ask_llm(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        """Helper function to send messages to the LLM and get a non-streamed response."""
        try:
            # Ensure llm is the Model object, not the litellm module
            if not hasattr(self.llm, 'send_completion'):
                self.io.tool_error("SearchEnhancer: LLM object does not have send_completion method.")
                return ""

            _hash, completion = self.llm.send_completion(
                messages=messages,
                functions=None,
                stream=False,
                temperature=temperature,
            )
            if completion and completion.choices and completion.choices[0].message:
                content = completion.choices[0].message.content
                if content:
                    return content.strip()
            self.io.tool_warning("SearchEnhancer: LLM returned empty or malformed response.")
            return ""
        except Exception as e:
            self.io.tool_error(f"SearchEnhancer: Error during LLM call: {e}")
            return ""

    def check_search_relevance(self, original_prompt: str) -> bool:
        """Asks LLM if web search is relevant for the given prompt."""
        messages = [
            {"role": "system", "content": "You are an AI assistant. Your task is to determine if a web search would likely provide relevant information to help answer the user's prompt. Respond with only 'YES' or 'NO'."},
            {"role": "user", "content": f"User prompt: \"{original_prompt}\"\n\nIs web search likely relevant for this prompt?"}
        ]
        response = self._ask_llm(messages, temperature=0.0)
        return response.upper() == "YES"

    def generate_search_queries(self, original_prompt: str) -> List[str]:
        """Asks LLM to generate 3 search queries based on the prompt."""
        messages = [
            {"role": "system", "content": "You are an AI assistant. Based on the user's prompt, generate exactly 3 concise search queries that would help find relevant information. Respond ONLY with a JSON object containing a single key 'queries' which is a list of 3 strings. Example: {\"queries\": [\"query one\", \"query two\", \"query three\"]}"},
            {"role": "user", "content": f"User prompt: \"{original_prompt}\"\n\nGenerate search queries."}
        ]
        response_str = self._ask_llm(messages)
        try:
            data = json.loads(response_str)
            queries = data.get("queries")
            if isinstance(queries, list) and len(queries) == 3 and all(isinstance(q, str) for q in queries):
                return queries
            else:
                self.io.tool_warning(f"SearchEnhancer: LLM returned malformed JSON for search queries: {response_str}")
        except json.JSONDecodeError:
            self.io.tool_warning(f"SearchEnhancer: LLM response for search queries was not valid JSON: {response_str}")
        # Fallback: try to generate queries from the prompt directly if JSON fails
        # This is a simple fallback, could be improved.
        # For now, let's return empty list on failure to ensure structured output.
        return []


    def _search_duckduckgo_urls(self, query: str, num_results: int = 10) -> List[str]:
        """
        Use DuckDuckGo's Instant Answer API to get top result URLs.
        Adapted from user-provided code.
        """
        urls_to_fetch = []
        try:
            api_url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "no_redirect": 1,
                "t": "aider_search_enhancer" # Application name for DDG API
            }
            resp = requests.get(api_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            collected_urls = []
            for item in data.get("Results", []):
                if item.get("FirstURL"):
                    collected_urls.append(item.get("FirstURL"))
            for topic in data.get("RelatedTopics", []):
                if "Topics" in topic:  # Group of sub-topics
                    for sub_topic in topic.get("Topics", []):
                        if sub_topic.get("FirstURL"):
                            collected_urls.append(sub_topic.get("FirstURL"))
                else:  # Single topic
                    if topic.get("FirstURL"):
                        collected_urls.append(topic.get("FirstURL"))
            
            # Deduplicate and limit
            seen = set()
            for u in collected_urls:
                if u and u not in seen:
                    seen.add(u)
                    urls_to_fetch.append(u)
                if len(urls_to_fetch) >= num_results:
                    break
        except requests.RequestException as e:
            # Handle errors (e.g., network issues, bad response)
            self.io.tool_warning(f"Error during DuckDuckGo search for '{query}': {e}")
        return urls_to_fetch

    def perform_web_search_and_get_urls(self, queries: List[str], max_unique_urls: int = 20) -> List[str]:
        """
        Performs web search for multiple queries and returns a deduplicated list of URLs.
        """
        all_urls = []
        # Aim for roughly max_unique_urls / len(queries) results per query,
        # but ensure at least a few results if many queries.
        results_per_query = max(3, (max_unique_urls + len(queries) -1) // len(queries) if queries else 0)

        for query in queries:
            all_urls.extend(self._search_duckduckgo_urls(query, num_results=results_per_query))

        # Deduplicate across all queries and limit
        seen_urls = set()
        unique_urls = []
        for url in all_urls:
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_urls.append(url)
            if len(unique_urls) >= max_unique_urls:
                break
        return unique_urls

    def _fetch_full_text_from_url(self, url: str, timeout: int = 10) -> str:
        """
        Fetches the HTML at `url`, strips scripts/styles, and returns
        the visible text from the <body>.
        Adapted from user-provided code.
        """
        try:
            headers = { # Some sites block requests without a common user-agent
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            resp = requests.get(url, timeout=timeout, headers=headers)
            resp.raise_for_status()
        except requests.RequestException as e:
            self.io.tool_warning(f"Error fetching {url}: {e}")
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form", "button", "input", "textarea", "select", "option"]):
            tag.decompose()
        
        # Try to get main content if available, otherwise body
        main_content = soup.find("main")
        if not main_content:
            article_content = soup.find("article")
            if not article_content:
                body = soup.body
            else:
                body = article_content
        else:
            body = main_content
        
        if not body: # Fallback if no body, main, or article
            text = soup.get_text(separator="\\n", strip=True)
        else:
            text = body.get_text(separator="\\n", strip=True)
        
        # Basic cleaning: reduce multiple newlines
        return "\\n".join([line for line in text.splitlines() if line.strip()])


    def fetch_content_for_urls(self, urls: List[str]) -> List[Dict[str, str]]:
        """
        Fetches full text content for a list of URLs.
        """
        fetched_data = []
        for url in urls:
            self.io.tool_output(f"Fetching content from: {url}", log_only=True) # User feedback
            text = self._fetch_full_text_from_url(url)
            if text: # Only add if text was successfully fetched
                # Limit text size early to avoid overly large payloads later
                max_text_len = 20000 # Approx 5k tokens, can be tuned
                if len(text) > max_text_len:
                    text = text[:max_text_len] + "\n... [TRUNCATED TEXT] ..."
                    self.io.tool_warning(f"Truncated fetched text from {url} to {max_text_len} chars.")
                fetched_data.append({"url": url, "full_text": text})
        return fetched_data

    def assess_results_utility(self, original_prompt: str, fetched_content: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Assesses the utility of each fetched content against the original prompt using LLM.
        """
        assessed_results = []
        for item in fetched_content:
            self.io.tool_output(f"Assessing utility of content from: {item['url']}", log_only=True)
            is_useful = False
            try:
                # Truncate full_text for this specific LLM call if it's very long
                text_for_assessment = item['full_text']
                # Max length for assessment prompt, can be tuned (e.g. 8000 chars ~ 2k tokens)
                max_assess_len = 8000
                if len(text_for_assessment) > max_assess_len:
                    text_for_assessment = text_for_assessment[:max_assess_len] + "\n... [TRUNCATED FOR ASSESSMENT] ..."

                messages = [
                    {"role": "system", "content": "You are an AI assistant. Your task is to determine if the provided text content is useful for answering the given user prompt. Respond ONLY with a JSON object containing a single key 'is_useful' which is a boolean (true or false). Example: {\"is_useful\": true}"},
                    {"role": "user", "content": f"User prompt: \"{original_prompt}\"\n\nText content from URL {item['url']}:\n\"\"\"\n{text_for_assessment}\n\"\"\"\n\nIs this content useful for answering the user prompt?"}
                ]
                
                response_str = self._ask_llm(messages, temperature=0.0)
                if response_str:
                    parsed_response = json.loads(response_str)
                    is_useful = parsed_response.get("is_useful", False)
                else: # LLM call failed or returned empty
                    self.io.tool_warning(f"SearchEnhancer: No response from LLM for utility assessment of {item['url']}")


            except json.JSONDecodeError:
                self.io.tool_warning(f"SearchEnhancer: Error decoding LLM JSON response for utility assessment of {item['url']}")
            except Exception as e:
                self.io.tool_error(f"SearchEnhancer: Error during LLM utility assessment for {item['url']}: {e}")
            
            assessed_results.append({**item, "is_useful": is_useful})
        return assessed_results

    def compile_useful_context_extracts(self, assessed_results: List[Dict[str, Any]], original_prompt: str) -> str:
        """
        Compiles extracts from useful content using LLM.
        """
        useful_texts_extracts = []
        for item in assessed_results:
            if item.get("is_useful"):
                self.io.tool_output(f"Extracting relevant parts from: {item['url']}", log_only=True)
                extract = ""
                try:
                    # Truncate full_text for this specific LLM call if it's very long
                    text_for_extraction = item['full_text']
                    # Max length for extraction prompt, can be tuned (e.g. 12000 chars ~ 3k tokens)
                    max_extract_len = 12000 
                    if len(text_for_extraction) > max_extract_len:
                         text_for_extraction = text_for_extraction[:max_extract_len] + "\n... [TRUNCATED FOR EXTRACTION] ..."

                    messages = [
                        {"role": "system", "content": "You are an AI assistant. Your task is to extract the most relevant sentences or paragraphs from the provided text content that directly help answer or provide context for the given user prompt. If no specific part of the text is highly relevant, respond with an empty string. Do not add any explanatory text, just the extracted content or an empty string."},
                        {"role": "user", "content": f"User prompt: \"{original_prompt}\"\n\nText content from URL {item['url']}:\n\"\"\"\n{text_for_extraction}\n\"\"\"\n\nExtract relevant parts:"}
                    ]
                    extract = self._ask_llm(messages)
                    
                    if extract.strip(): # Add only if extract is not empty
                        useful_texts_extracts.append(f"Source: {item['url']}\n{extract.strip()}\n---")
                except Exception as e:
                    self.io.tool_error(f"SearchEnhancer: Error during LLM context extraction for {item['url']}: {e}")
                    useful_texts_extracts.append(f"Source: {item['url']}\nError extracting content.\n---")
        
        return "\\n\\n".join(useful_texts_extracts)

if __name__ == '__main__':
    # Basic test (requires aider.llm.LLM and aider.io.InputOutput to be defined or mocked)
    class MockModel:
        def __init__(self, name="mock-model"):
            self.name = name
            # Mock .info attribute if SearchEnhancer or other parts rely on it
            self.info = {"input_cost_per_token": 0, "output_cost_per_token": 0, "max_input_tokens": 4096}


        def send_completion(self, messages, functions, stream, temperature):
            # Simulate LLM responses for testing
            # This mock needs to be more sophisticated to handle different prompts correctly
            last_message_content = messages[-1]["content"]
            response_content = ""

            if "Is web search likely relevant" in last_message_content:
                if "python" in last_message_content.lower():
                    response_content = "YES"
                else:
                    response_content = "NO"
            elif "Generate search queries" in last_message_content:
                response_content = json.dumps({"queries": ["query for python", "another python query", "last python query"]})
            elif "Is this content useful" in last_message_content:
                if "example.com/useful" in last_message_content or "highly relevant" in last_message_content.lower() :
                    response_content = json.dumps({"is_useful": True})
                else:
                    response_content = json.dumps({"is_useful": False})
            elif "Extract relevant parts" in last_message_content:
                if "example.com/useful" in last_message_content or "highly relevant" in last_message_content.lower():
                    response_content = "This is a very relevant sentence from the useful page about Python."
                else:
                    response_content = ""
            
            # Mocking the completion object structure expected by _ask_llm
            class MockChoice:
                def __init__(self, content):
                    self.message = MockMessage(content)
            class MockMessage:
                def __init__(self, content):
                    self.content = content
            class MockCompletion:
                def __init__(self, content):
                    self.choices = [MockChoice(content)]
            
            return hashlib.sha1(), MockCompletion(response_content)


    class MockIO:
        def __init__(self):
            self.args = argparse.Namespace(search_mode=True) # Mock args

        def tool_output(self, message, log_only=False, bold=False):
            print(f"IO: {message}")
        def tool_warning(self, message):
            print(f"IO WARNING: {message}")
        def tool_error(self, message):
            print(f"IO ERROR: {message}")

    mock_llm_instance = MockModel()
    mock_io_instance = MockIO()
    enhancer = SearchEnhancer(llm=mock_llm_instance, io=mock_io_instance)

    test_prompt = "Tell me about python programming benefits"

    # Test 0: Relevance Check
    print("\\n--- Test: check_search_relevance ---")
    is_relevant = enhancer.check_search_relevance(test_prompt)
    print(f"Search relevant for '{test_prompt}': {is_relevant}")
    
    is_relevant_false = enhancer.check_search_relevance("Tell me a joke")
    print(f"Search relevant for 'Tell me a joke': {is_relevant_false}")

    # Test 0.5: Query Generation
    print("\\n--- Test: generate_search_queries ---")
    if is_relevant:
        queries = enhancer.generate_search_queries(test_prompt)
        print(f"Generated queries for '{test_prompt}': {queries}")
    else:
        print("Skipping query generation as not relevant.")


    # Test 1: _search_duckduckgo_urls
    print("\\n--- Test: _search_duckduckgo_urls ---")
    # Using generated queries if available, else default
    generated_queries_for_test = queries if is_relevant and queries else ["python programming benefits", "why use python"]
    
    python_urls = enhancer._search_duckduckgo_urls(generated_queries_for_test[0], num_results=2)
    print(f"URLs for '{generated_queries_for_test[0]}': {python_urls}")

    # Test 2: perform_web_search_and_get_urls
    print("\\n--- Test: perform_web_search_and_get_urls ---")
    multi_query_urls = enhancer.perform_web_search_and_get_urls(generated_queries_for_test, max_unique_urls=3)
    print(f"URLs for multiple queries: {multi_query_urls}")

    # Test 4: fetch_content_for_urls
    print("\\n--- Test: fetch_content_for_urls ---")
    # Use real URLs if found, otherwise mock. For safety, let's use example.com for general tests.
    urls_to_actually_fetch = multi_query_urls[:2] if multi_query_urls else ["http://example.com/useful", "http://example.com/irrelevant"]
    
    # To make the test more robust with mock LLM, let's ensure one URL is "useful"
    # and its content reflects that for the mock LLM.
    # We'll simulate fetching by creating the structure `fetch_content_for_urls` expects.
    
    simulated_fetched_content = []
    if urls_to_actually_fetch:
        # Simulate fetching for the first URL, making it "useful"
        simulated_fetched_content.append(
            {"url": urls_to_actually_fetch[0], "full_text": "This page contains highly relevant information about Python benefits and programming."}
        )
        # Simulate fetching for a second URL, making it "irrelevant"
        if len(urls_to_actually_fetch) > 1:
             simulated_fetched_content.append(
                {"url": urls_to_actually_fetch[1], "full_text": "This page is about unrelated topics like cooking recipes."}
            )
        else: # ensure we have at least two items for assessment test
            simulated_fetched_content.append(
                {"url": "http://example.com/another_irrelevant", "full_text": "More unrelated stuff."}
            )

    print(f"Simulated fetched content for assessment: {simulated_fetched_content}")
    
    # Test 5 & 6: assess_results_utility and compile_useful_context_extracts (using mock LLM)
    print("\\n--- Test: assess_results_utility & compile_useful_context_extracts ---")
        
    assessed_results_live = enhancer.assess_results_utility(test_prompt, simulated_fetched_content)
    print(f"Assessed results (live test with mock LLM): {assessed_results_live}")
    
    compiled_extracts_live = enhancer.compile_useful_context_extracts(assessed_results_live, test_prompt)
    print(f"Compiled extracts (live test with mock LLM):\\n{compiled_extracts_live}")

    print("\\n--- End of Tests ---")

# Need to import argparse for the mock IO's args
import argparse
