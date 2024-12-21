import os
import logging
from openai import OpenAI
from litellm.utils import ModelResponse

class CompatibleOpenaiApi:
    def __init__(self):
        api_key = os.environ.get("COMPATIBLE_OPENAI_API_KEY")
        api_base = os.environ.get("COMPATIBLE_OPENAI_API_BASE")
        if not api_key or not api_base:
            return

        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base
        )

    def chat_completion(self, model, messages, stream=False, temperature=0.7):
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=stream,
                temperature=temperature
            )
            if stream:
                return convert_to_litellm_response(response)
            else:
                return ModelResponse(**response.model_dump())
        except Exception as e:
            return {"error": str(e)}

def convert_to_litellm_response(response):
    class ReusableStream:
        def __init__(self, stream):
            self.stream = stream
            self._cached_chunks = []
            self._finished = False
            self.choices = []
        
        def __iter__(self):
            if self._finished:
                for chunk in self._cached_chunks:
                    yield chunk
                return
            
            try:
                for chunk in self.stream:
                    if hasattr(chunk, 'choices') and chunk.choices:
                        self._cached_chunks.append(chunk)
                        yield chunk
                self._finished = True
            except Exception as e:
                print(str(e))
                raise
    
    wrapped_stream = ReusableStream(response)
    wrapped_stream.choices = []
    return wrapped_stream
