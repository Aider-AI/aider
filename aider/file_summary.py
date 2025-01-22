import os
import hashlib
from pathlib import Path
from diskcache import Cache
from tqdm import tqdm
import signal

from aider.sendchat import simple_send_with_retries, send_completion
import time

class FileSummary:
    BYTES_PER_TOKEN = 4  # Approximate bytes per token

    def __init__(self, io, cache, model, fname):
        self.io = io
        self.model = model
        self.cache = cache
        self.fname = fname
        self.last_size = 0
        self.last_mtime = 0

        self.chunk_size = int(model.max_chat_history_tokens * 0.8) or 2000
        self.overlap = 200  # Tokens overlap between chunks
        
        self.loaded = False
        self.summary = None

    def has_changed(self):
        """Check if the file has changed since last summary generation"""

        file_size = os.path.getsize(self.fname)
        if file_size != self.last_size:
            return True
        
        current_mtime = os.path.getmtime(self.fname)
        if current_mtime != self.last_mtime:
            return True
        
        return False
    
    def get_file_hash(self):
        """Get a hash of the file contents for change detection"""
        content = self.io.read_text(self.fname)
        if not content:
            return None
        return hashlib.sha256(content.encode()).hexdigest()

    def chunk_file(self, content):
        """Split file content into chunks intelligently based on content structure"""
        # If content is small enough, return as single chunk
        if len(content) <= self.chunk_size * self.BYTES_PER_TOKEN:  # Using 4 chars per token as approximation
            return [content]

        chunks = []
        start = 0
        content_len = len(content)

        # Common code block delimiters
        block_starts = {'{', '(', '[', '"""', "'''"}
        block_ends = {'}', ')', ']', '"""', "'''"}
        
        while start < content_len:
            # Calculate the ideal end point
            ideal_end = start + self.chunk_size * self.BYTES_PER_TOKEN
            
            if ideal_end >= content_len:
                chunks.append(content[start:])
                break

            # Look for a good splitting point
            end = ideal_end
            
            # First try to find a blank line near the ideal end
            blank_line = content.rfind('\n\n', start + self.chunk_size * 2, ideal_end + self.chunk_size)
            if blank_line != -1:
                end = blank_line + 2
            else:
                # Try to find a newline
                newline = content.rfind('\n', start + self.chunk_size * 2, ideal_end + self.chunk_size)
                if newline != -1:
                    # Check if we're in the middle of a block
                    section = content[start:newline]
                    
                    # Count block delimiters
                    block_level = 0
                    for char in section:
                        if char in block_starts:
                            block_level += 1
                        elif char in block_ends:
                            block_level -= 1
                    
                    # If we're not in the middle of a block, use this split point
                    if block_level == 0:
                        end = newline + 1
                    else:
                        # Look for the end of the current block
                        for i in range(newline, min(newline + self.chunk_size, content_len)):
                            if content[i] in block_ends:
                                block_level -= 1
                                if block_level == 0:
                                    end = i + 1
                                    break

            # If the line is too long, force a split
            if end <= start:
                end = start + self.chunk_size * self.BYTES_PER_TOKEN

            # Extract chunk with overlap
            chunk = content[start:end]
            chunks.append(chunk)
            
            # Move start position for next chunk, including overlap
            start = max(start + self.chunk_size * 2, end - self.overlap)

        return chunks

    def summarize_chunk(self, chunk, chunk_index=0, previous_summaries=None, pbar=None):
        """Summarize a single chunk using the LLM, with context from previous chunks"""
        system_msg = (
            "You are a helpful assistant that summarizes files. If the file contains code, provide a summary of "
            "the code, function names, arguements, and description of the function along with hierarchical information. If "
            "the file contains formatted text, provide a context-preserving hierarchical summarization of each block while "
            "identifying the values. Maintain the hierarchical information in a schema format in a \"hierarchy\" section of the "
            "summary. Do not duplicate object layots in the schema, generalize it and provide options in the schema "
            "You will be provided chunks of the file to summarize so you are working with incomplete "
            "data, a later stage will combine all the summaries into a single summary."
        )

        content_msg = f"Please summarize this section (chunk {chunk_index}) of a file:\n\n{chunk}"
        
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": content_msg}
        ]

        # Initialize variables for progress tracking
        completion_text = ""
        hourglass_chars = "⌛⏳"
        hourglass_idx = 0
        last_hourglass_time = 0
        hourglass_delay = 0.5

        try:
            completion = send_completion(
                self.model.name,
                messages,
                None,
                stream=False,  # Changed to False for testing
                temperature=0,
                extra_params=self.model.extra_params,
            )
            
            for chunk in completion[1]:
                try:
                    text = chunk.choices[0].delta.content
                    if text:
                        completion_text += text
                        
                        # Update hourglass animation
                        current_time = time.time()
                        if current_time - last_hourglass_time >= hourglass_delay:
                            last_hourglass_time = current_time
                            hourglass = hourglass_chars[hourglass_idx]
                            hourglass_idx = (hourglass_idx + 1) % len(hourglass_chars)
                            if pbar:
                                pbar.set_postfix_str(f"{hourglass} Processing chunk {chunk_index}")
                except AttributeError:
                    pass
                    
            pbar.set_postfix_str(f"✓ Completed chunk {chunk_index}")
            
        except Exception as e:
            self.io.tool_error(f"Failed to generate summary for chunk {chunk_index} of {self.fname}: {str(e)}")
            return None, 0, 0, 0

        completion_text = completion_text.strip()
        if completion_text and completion_text[0] == '"' and completion_text[-1] == '"':
            completion_text = completion_text[1:-1].strip()

        # Get token counts and costs from the completion object
        completion_obj = completion[0]
        prompt_tokens = completion_obj.usage.prompt_tokens if hasattr(completion_obj, 'usage') else 0
        completion_tokens = completion_obj.usage.completion_tokens if hasattr(completion_obj, 'usage') else 0
        
        input_cost_per_token = self.model.info.get("input_cost_per_token") or 0
        output_cost_per_token = self.model.info.get("output_cost_per_token") or 0
        
        cost = (prompt_tokens * input_cost_per_token) + (completion_tokens * output_cost_per_token)

        return completion_text, prompt_tokens, completion_tokens, cost

    def summarize_all_chunks(self, summaries, pbar=None):
        """Combine chunk summaries into a single summary, respecting token limits"""
        if not summaries:
            return None, 0, 0, 0

        # Helper function to estimate tokens
        def estimate_tokens(text):
            return len(text) // self.BYTES_PER_TOKEN if text else 0

        # Helper function to combine a subset of summaries
        def combine_subset(subset_summaries):
            system_msg = (
                "You are a helpful assistant that summarizes files. A previous assistant has already summarized the file "
                "in to chunks with an overlap of content, so some information in the summaries may be duplicated. Your task is to "
                "combine these summaries into a single coherent summary. Use the schema format in the hierarchy section of each chunk "
                "summary to define an overall heirarchy schema representation of the file."
            )

            content_msg = f"Please summarize these chunks into a single summary:\n\n"
            for i, summary in enumerate(subset_summaries):
                content_msg += f"Chunk summary{i}:\n{summary}\n\n"

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": content_msg}
            ]

            completion_text = ""
            try:
                completion = send_completion(
                    self.model.name,
                    messages,
                    None,
                    stream=True,
                    temperature=0,
                    extra_params=self.model.extra_params,
                )
                
                hourglass_chars = "⌛⏳"
                hourglass_idx = 0
                last_hourglass_time = 0
                hourglass_delay = 0.5
                
                for chunk in completion[1]:
                    try:
                        text = chunk.choices[0].delta.content
                        if text:
                            completion_text += text
                            
                            # Update hourglass animation
                            current_time = time.time()
                            if current_time - last_hourglass_time >= hourglass_delay:
                                last_hourglass_time = current_time
                                hourglass = hourglass_chars[hourglass_idx]
                                hourglass_idx = (hourglass_idx + 1) % len(hourglass_chars)
                                if pbar:
                                    pbar.set_postfix_str(f"{hourglass} Combining summaries...")
                    except AttributeError:
                        pass
                        
                pbar.set_postfix_str(f"✓ Combining summaries complete")
                
            except Exception as e:
                self.io.tool_error(f"Failed to generate summary for {self.fname}: {str(e)}")
                return None, 0, 0, 0

            completion_text = completion_text.strip()
            if completion_text and completion_text[0] == '"' and completion_text[-1] == '"':
                completion_text = completion_text[1:-1].strip()

            # Get token counts and costs from the completion object
            completion_obj = completion[0]
            prompt_tokens = completion_obj.usage.prompt_tokens if hasattr(completion_obj, 'usage') else 0
            completion_tokens = completion_obj.usage.completion_tokens if hasattr(completion_obj, 'usage') else 0
            
            input_cost_per_token = self.model.info.get("input_cost_per_token") or 0
            output_cost_per_token = self.model.info.get("output_cost_per_token") or 0
            
            cost = (prompt_tokens * input_cost_per_token) + (completion_tokens * output_cost_per_token)

            return completion_text, prompt_tokens, completion_tokens, cost

        # Calculate max tokens we can use for summaries
        max_tokens = self.model.max_chat_history_tokens
        if not max_tokens:
            max_tokens = 4096  # Default fallback
        
        # Reserve tokens for system message and overhead
        available_tokens = max_tokens - 500  # Reserve tokens for prompts and overhead
        
        # Try to combine all summaries at once first
        total_tokens = sum(estimate_tokens(s) for s in summaries)
        if total_tokens <= available_tokens:
            return combine_subset(summaries)

        # If that's too big, split into smaller groups and combine recursively
        result_summaries = []
        current_group = []
        current_tokens = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_cost = 0

        for summary in summaries:
            summary_tokens = estimate_tokens(summary)
            if current_tokens + summary_tokens > available_tokens:
                if current_group:  # Combine current group
                    combined, prompt_tokens, completion_tokens, cost = combine_subset(current_group)
                    if combined:
                        result_summaries.append(combined)
                        total_prompt_tokens += prompt_tokens
                        total_completion_tokens += completion_tokens
                        total_cost += cost
                current_group = [summary]
                current_tokens = summary_tokens
            else:
                current_group.append(summary)
                current_tokens += summary_tokens

        if current_group:  # Don't forget the last group
            combined, prompt_tokens, completion_tokens, cost = combine_subset(current_group)
            if combined:
                result_summaries.append(combined)
                total_prompt_tokens += prompt_tokens
                total_completion_tokens += completion_tokens
                total_cost += cost

        # If we still have multiple summaries, combine them recursively
        if len(result_summaries) > 1:
            # Calculate number of recursive iterations needed
            num_summaries = len(result_summaries)
            num_iterations = 0
            while num_summaries > 1:
                num_summaries = (num_summaries + 1) // 2
                num_iterations += 1
            
            if pbar:
                # Reset progress bar for recursive combining
                pbar.reset(total=num_iterations)
                pbar.set_description("Recursively combining summaries")
                iteration = 0
            
            final_summary, prompt_tokens, completion_tokens, cost = self.summarize_all_chunks(result_summaries, pbar=pbar)
            
            if pbar:
                iteration += 1
                pbar.update(1)
                pbar.set_postfix_str(f"Iteration {iteration}/{num_iterations}")
            
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_cost += cost
            return final_summary, total_prompt_tokens, total_completion_tokens, total_cost
        elif result_summaries:
            return result_summaries[0], total_prompt_tokens, total_completion_tokens, total_cost
        
        return None, 0, 0, 0
    
    def get_chunk_hash(self, chunk):
        """Get hash of a chunk's content"""
        return hashlib.sha256(chunk.encode()).hexdigest()
    
    def summarize(self):
        # Generate new summary
        content = self.io.read_text(self.fname)
        if not content:
            self.io.tool_error(f"Failed to read content from {self.fname}")
            return None

        chunks = self.chunk_file(content)
        summaries = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_cost = 0
        
        def handle_interrupt(signum, frame):
            self.io.tool_warning("\nSummarization cancelled by user")
            pbar.close()
            raise KeyboardInterrupt
        
        # Setup progress bar with operation status
        fname = self.fname
        if len(fname) > 50:
            fname = "..." + fname[-48:] 
        pbar = tqdm(total=len(chunks), desc=f"Summarizing {fname}", 
                   bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} chunks{postfix}')
        pbar.set_postfix_str("Starting...")

        # Setup signal handler
        original_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, handle_interrupt)
        
        try:
            for i, chunk in enumerate(chunks):
                # Pass previous summaries as context
                summary, prompt_tokens, completion_tokens, cost = self.summarize_chunk(
                    chunk, 
                    chunk_index=i,
                    previous_summaries=summaries if summaries else None,
                    pbar=pbar
                )
                if summary is None:
                    pbar.close()
                    return None
                    
                summaries.append(summary)
                total_prompt_tokens += prompt_tokens
                total_completion_tokens += completion_tokens
                total_cost += cost
                
                pbar.update(1)

            # Combine summaries
            pbar.set_postfix_str("⏳ Combining all summaries...")
            final_summary, prompt_tokens, completion_tokens, cost = self.summarize_all_chunks(summaries, pbar=pbar)
        finally:
            pbar.close()
            # Restore original signal handler
            signal.signal(signal.SIGINT, original_handler)
        if final_summary is None:
            return None
            
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        total_cost += cost

        self.loaded = True
        self.last_mtime = os.path.getmtime(self.fname)
        self.last_size = os.path.getsize(self.fname)
        self.summary = final_summary

        # Cache the result
        self.cache[self.fname] = {
            "mtime": self.last_mtime,
            "size": self.last_size,
            "summary": final_summary
        }

        # Report token usage
        if hasattr(self.io, 'coder'):
            coder = self.io.coder
            coder.message_tokens_sent += total_prompt_tokens
            coder.message_tokens_received += total_completion_tokens
            coder.total_cost += total_cost
            coder.message_cost += total_cost
            
            tokens_report = f"Tokens for summarizing {self.fname}: {total_prompt_tokens:,} sent, {total_completion_tokens:,} received."
            cost_report = f"Cost: ${total_cost:.4f}"
            self.io.tool_output(f"{tokens_report} {cost_report}")

    def get_summary(self):
        """Get cached summary or generate new one"""
        
        if not self.loaded:
            cached = self.cache.get(self.fname)
            if cached:
                self.last_mtime = cached.get("mtime", 0)
                self.last_size = cached.get("size", 0)
                self.summary = cached.get("summary")
                self.chunk_hashes = cached.get("chunk_hashes")
                self.loaded = True

        if not self.has_changed():
            return self.summary
        
        self.summarize()        

        return self.summary
