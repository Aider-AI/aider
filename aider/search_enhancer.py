import asyncio
import json
import os
from typing import List, Dict, Any

# For Browser-Use
from browser_use import Agent as BrowserUseAgent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from dotenv import load_dotenv

# For parsing HTML if fetch_url_content needs it
from bs4 import BeautifulSoup

# Retain aider's LLM type hint if possible, or use Any
# from aider.llm import LLM # Assuming this is the type for aider's main LLM

class SearchEnhancer:
    def __init__(self, llm, io, args=None): # llm: Model (aider's), io: InputOutput, args: for config
        self.llm = llm # LLM for generating Browser-Use task instruction
        self.io = io
        self.args = args
        self.browser_instance = None
        self.llm_for_browser_use = None

        if not self.args:
            self.io.tool_warning("SearchEnhancer: self.args not provided. Browser-Use functionality will be disabled.")
            return

        try:
            load_dotenv() # Load .env file for API keys if present
            
            deepseek_api_key_val = getattr(self.args, 'deepseek_api_key', None) or os.getenv("DEEPSEEK_API_KEY")
            if not deepseek_api_key_val:
                self.io.tool_error("SearchEnhancer: DEEPSEEK_API_KEY not found in args or environment. Browser-Use will be disabled.")
                return

            self.llm_for_browser_use = ChatOpenAI(
                base_url='https://api.deepseek.com/v1',
                model=getattr(self.args, 'deepseek_model_name', 'deepseek-chat'), # e.g., deepseek-chat
                api_key=SecretStr(deepseek_api_key_val),
                temperature=0.0
            )
            self.io.tool_output("SearchEnhancer: DeepSeek LLM for Browser-Use initialized.")

            browser_path = getattr(self.args, 'browser_use_real_browser_path', None)
            headless_default = not browser_path # Headless if no specific browser path
            headless = getattr(self.args, 'browser_use_headless', headless_default)
            
            browser_config_params = {
                "headless": headless,
                "disable_security": True  # Often helpful for automation
            }
            if browser_path:
                # Assuming if a path is given, it's for a Chrome-like browser as hinted by Browser-Use error
                browser_config_params["chrome_instance_path"] = browser_path
            
            browser_config = BrowserConfig(**browser_config_params)
            self.browser_instance = Browser(config=browser_config)
            self.io.tool_output(f"SearchEnhancer: Browser-Use Browser initialized (headless: {headless}, path: {browser_path or 'default'}).")

        except Exception as e:
            self.io.tool_error(f"SearchEnhancer: Error during initialization: {e}. Browser-Use may be disabled.")
            self.browser_instance = None
            self.llm_for_browser_use = None

    def _sync_run_async(self, coro):
        """Helper to run an async coroutine synchronously."""
        try:
            # Attempt to get the current running loop in the current OS thread.
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # If a loop is running, we cannot use asyncio.run().
                # This scenario is complex if called from a synchronous context.
                # Ideally, the caller should be async or manage thread safety.
                # For now, we'll log a warning and attempt to schedule it if possible,
                # but this might not work as expected without further infrastructure.
                self.io.tool_warning(
                    "SearchEnhancer: _sync_run_async called when a loop is running. " 
                    "Attempting to create task. This may not work correctly from sync code."
                )
                # This is not ideal from a truly synchronous function without knowing more about the loop.
                # A more robust solution would involve asyncio.run_coroutine_threadsafe if in a different thread,
                # or making the calling chain async.
                # As a fallback that might work in some contexts (but can cause issues):
                future = asyncio.ensure_future(coro, loop=loop)
                return loop.run_until_complete(future) # This blocks, but might conflict with outer loop management.
            else:
                # If loop.is_running() is false, it means get_running_loop() returned a loop
                # that is not currently running, or get_event_loop() was implicitly called and returned one.
                # asyncio.run() should be safe here as it creates a new loop if needed.
                return asyncio.run(coro)
        except RuntimeError as e:
            # This typically means "asyncio.run() cannot be called when another asyncio event loop is running"
            # OR "no event loop ... and no current event loop set".
            if "no current event loop" in str(e) or "cannot be called when another" not in str(e).lower():
                # If no loop exists, asyncio.run() is the right tool.
                try:
                    return asyncio.run(coro)
                except Exception as run_e:
                    self.io.tool_error(f"SearchEnhancer: Error in asyncio.run within _sync_run_async: {run_e}")
                    return None
            else:
                # Loop is running, and asyncio.run() failed as expected.
                # This reiterates the complex scenario above.
                self.io.tool_error(f"SearchEnhancer: asyncio runtime error in _sync_run_async (loop already running): {e}. Coroutine not run.")
                return None
        except Exception as e:
            self.io.tool_error(f"SearchEnhancer: Unexpected error in _sync_run_async: {e}")
            return None

    def _ask_llm_for_browser_task_instruction(self, original_user_query: str) -> str:
        """Uses the main LLM (from AgentCoder) to generate a task instruction for Browser-Use."""
        line1 = f"""Given the user's information need: \"{original_user_query}\"\n\n"""
        line2 = "Formulate a concise, actionable task for an AI-driven web browsing agent (which uses the DeepSeek LLM). "
        line3 = "The task should instruct the agent to find the relevant information and then compile and return a comprehensive textual summary of its findings. "
        line4 = "The output summary should be directly usable as context for the original user need. "
        line5 = "Be specific about what information to look for and what the final summary should contain. "
        line6 = "The browser agent can navigate websites, read content, and interact with elements if necessary. "
        line7 = "Task Instruction:"
        prompt = line1 + line2 + line3 + line4 + line5 + line6 + line7
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            # Assuming self.llm is an Aider Coder instance which has a 'send' method for streaming
            # and 'main_model' attribute for model name.
            if hasattr(self.llm, 'send') and hasattr(self.llm, 'main_model'):
                full_response_content = ""
                # Ensure partial_response_content exists if Coder expects it
                if hasattr(self.llm, 'partial_response_content'): 
                    self.llm.partial_response_content = ""
                
                # Iterate over the streaming response from Coder.send
                # This might need adjustment if Coder.send has a non-streaming mode or a helper for it.
                # For now, accumulating the stream.
                response_stream = self.llm.send(
                    messages,
                    model=self.llm.main_model, # Use the Coder's main_model
                    functions=None, 
                    temperature=0.1 # Low temperature for task generation
                )
                for chunk in response_stream:
                    if chunk: # Ensure chunk is not None or empty
                        full_response_content += chunk
                
                if full_response_content.strip():
                    return full_response_content.strip()
                else:
                    self.io.tool_warning("SearchEnhancer: LLM (Coder.send) returned empty response for browser task generation.")
            else:
                self.io.tool_error(
                    "SearchEnhancer: Main LLM object (self.llm) does not have the expected 'send' and 'main_model' attributes. "
                    "Cannot generate browser task instruction."
                )
        except Exception as e:
            self.io.tool_error(f"SearchEnhancer: Error generating browser task instruction via LLM: {e}")
        
        # Fallback instruction if LLM fails
        return f"Based on the user query \"{original_user_query}\", find relevant information and provide a comprehensive summary."


    def perform_browser_task(self, original_user_query: str) -> str:
        """
        Uses Browser-Use with DeepSeek to perform a web task based on the original_user_query.
        Returns a textual summary of the findings.
        """
        if not self.browser_instance or not self.llm_for_browser_use:
            self.io.tool_warning("SearchEnhancer: Browser-Use components not initialized. Skipping web task.")
            return ""

        self.io.tool_output(f"SearchEnhancer: Generating task for Browser-Use based on: {original_user_query[:100]}...")
        browser_agent_task_instruction = self._ask_llm_for_browser_task_instruction(original_user_query)
        
        if not browser_agent_task_instruction or browser_agent_task_instruction.startswith("Based on the user query"):
            self.io.tool_error("SearchEnhancer: Failed to generate a specific task instruction for Browser-Use, or using fallback.")
            # If using fallback, we might still proceed if it's deemed useful enough.
            if not browser_agent_task_instruction: # Complete failure
                 return ""
            
        self.io.tool_output(f"SearchEnhancer: Browser-Use task: {browser_agent_task_instruction}")

        try:
            bu_agent = BrowserUseAgent(
                task=browser_agent_task_instruction,
                llm=self.llm_for_browser_use,
                browser=self.browser_instance,
                use_vision=False,
            )
            
            self.io.tool_output("SearchEnhancer: Running Browser-Use agent...")
            result = self._sync_run_async(bu_agent.run()) # MODIFIED: Use _sync_run_async with agent.run()

            if result is None: # _sync_run_async might return None on error
                self.io.tool_error("SearchEnhancer: Browser-Use agent execution failed or returned None.")
                return ""
                
            if isinstance(result, dict) and "output" in result:
                result_text = str(result["output"])
            elif isinstance(result, str):
                result_text = result
            else:
                self.io.tool_warning(f"SearchEnhancer: Browser-Use agent returned an unexpected result type: {type(result)}. Content: {str(result)[:200]}")
                result_text = str(result) if result is not None else ""

            self.io.tool_output(f"SearchEnhancer: Browser-Use agent finished. Result snippet: {result_text[:200]}...")
            return result_text

        except Exception as e:
            self.io.tool_error(f"SearchEnhancer: Error during Browser-Use agent execution: {e}")
            import traceback
            self.io.tool_error(traceback.format_exc())
            return ""
        finally:
            pass # Browser closing handled by close_browser() method

    async def _fetch_url_content_async(self, url: str) -> str:
        """Async helper to fetch and parse URL content using Playwright via Browser-Use Browser."""
        if not self.browser_instance:
            self.io.tool_warning("SearchEnhancer: Browser-Use Browser not initialized for _fetch_url_content_async. Cannot fetch URL.")
            return ""
        # Further check if browser_instance is usable (e.g. underlying playwright browser is connected)
        if not hasattr(self.browser_instance, 'new_page') or not self.browser_instance._browser:
            self.io.tool_error("SearchEnhancer: Browser-Use Browser internal state seems invalid. Cannot fetch URL.")
            return ""

        page = None
        cleaned_text = "" # Initialize to ensure it's defined
        try:
            page = await self.browser_instance.new_page() # This is an async call
            await page.goto(url, timeout=getattr(self.args, 'browser_use_page_timeout', 30000)) # Default 30s timeout
            html_content = await page.content()

            # Use BeautifulSoup to parse and extract text
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Remove script, style, and other non-content tags
            for tag_name in ["script", "style", "noscript", "header", "footer", "nav", "aside", "form", "button", "input", "textarea", "select", "option"]:
                for tag in soup.find_all(tag_name): # Iterate over actual found tags
                    tag.decompose()
            
            main_content = soup.find("main")
            if not main_content:
                article_content = soup.find("article")
                body_like_content = article_content if article_content else soup.body
            else:
                body_like_content = main_content
            
            text = ""
            if body_like_content:
                text = body_like_content.get_text(separator="\\n", strip=True)
            else: # Fallback if no main structural tags found
                text = soup.get_text(separator="\\n", strip=True)
            
            # Basic cleaning: reduce multiple newlines
            cleaned_text = "\\n".join([line for line in text.splitlines() if line.strip()])
            
            # Limit text size
            max_text_len = getattr(self.args, 'browser_use_max_content_length', 20000)
            if len(cleaned_text) > max_text_len:
                cleaned_text = cleaned_text[:max_text_len] + "\\n... [TRUNCATED TEXT] ..."
                self.io.tool_warning(f"SearchEnhancer: Truncated fetched text from {url} to {max_text_len} chars.")
            
            # Return cleaned_text from within the try block if successful
            return cleaned_text

        except Exception as e:
            self.io.tool_error(f"SearchEnhancer: Error fetching or parsing {url}: {e}")
            import traceback
            self.io.tool_error(traceback.format_exc()) # Log full traceback
            return "" # Return empty string on error
        finally:
            if page:
                try:
                    await page.close()
                except Exception as e:
                    self.io.tool_warning(f"SearchEnhancer: Error closing page for {url}: {e}")
    
    def fetch_url_content(self, url: str) -> str:
        """Synchronous wrapper for fetching URL content."""
        return self._sync_run_async(self._fetch_url_content_async(url))


    def close_browser(self):
        """Closes the Browser-Use browser instance if it's open."""
        if self.browser_instance:
            try:
                self.io.tool_output("SearchEnhancer: Closing Browser-Use browser...")
                # Browser.close() is async
                self._sync_run_async(self.browser_instance.close())
                self.browser_instance = None
                self.io.tool_output("SearchEnhancer: Browser-Use browser closed.")
            except Exception as e:
                self.io.tool_error(f"SearchEnhancer: Error closing browser: {e}")

    # Removed old methods:
    # - check_search_relevance
    # - generate_search_queries
    # - _search_duckduckgo_urls
    # - perform_web_search_and_get_urls
    # - _fetch_full_text_from_url (replaced by fetch_url_content using Browser-Use)
    # - fetch_content_for_urls
    # - assess_results_utility
    # - compile_useful_context_extracts

    # Mock classes (if any were here for testing) would also be removed or updated.
    # For this refactor, I'm focusing on the main class logic.

# Example of how AgentCoder might use the new SearchEnhancer (conceptual)
# class AgentCoder:
#     def __init__(self, ...):
#         # ...
#         if self.args.agent_web_search != "never":
#             self.search_enhancer = SearchEnhancer(self.planner_llm or self.main_model, self.io, self.args)
#     
#     def some_phase_needing_search(self, query):
#         # ...
#         if self.search_enhancer:
#             web_results = self.search_enhancer.perform_browser_task(query)
#             # Use web_results
#         # ...
# 
#     def __del__(self): # Or a more explicit cleanup method
#         if hasattr(self, 'search_enhancer') and self.search_enhancer:
#             self.search_enhancer.close_browser()

# Main execution part for standalone testing (if any) should be updated or removed.
# if __name__ == \'__main__\':
#   pass # Update for new SearchEnhancer
