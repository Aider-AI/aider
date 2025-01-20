from typing import Callable, Tuple
from regex import findall

from aider.coders.base_coder import Coder
"""Perform a coding task on multiple files in batches that fit the context and outpot token limits, without sending them all at once."""
class IterateCoder(Coder):
    coder : Coder = None
    original_kwargs: dict = None
    edit_format = "iterate"
    
    def __init__(self, main_model, io, **kwargs):
        super().__init__(main_model, io,**kwargs)

    def run_one(self, user_message, preproc):
        if self.coder is None:
            self.coder = self.coder = Coder.create(main_model=self.main_model, edit_format=self.main_model.edit_format,from_coder=self,**self.original_kwargs)
        remaining_files_with_type_length : list[Tuple[str,bool,int]]=[] #save these to avoid double reads
        for f in self.abs_fnames: #abs_fnames and abs_readonly_fnames change type, not bothering to use methods.
                remaining_files_with_type_length.append((f, True, self.main_model.token_count(self.io.read_text(f))))
        for f in self.abs_read_only_fnames:
                remaining_files_with_type_length.append((f,False,self.main_model.token_count(self.io.read_text(f))))
        max_tokens = self.main_model.info.get('max_tokens')
        max_context = self.main_model.info['max_input_tokens']
        max_output = self.main_model.info['max_output_tokens']
        repo_tokens = self.main_model.get_repo_map_tokens()
        sent_tokens = self.message_tokens_sent
        received_tokens = self.message_tokens_received
        """fitting input files + chat history + repo_map + files_to_send to context limit and
        files_to_send to the output_token limit.
        output files are assumed to be greater in size than the input files"""
        for files_to_send_with_types in self.file_cruncher( max_context=max_context,
        max_output= max_tokens if max_tokens is not None else max_output,
        chat_history_tokens=repo_tokens + sent_tokens + received_tokens,remaining_files=remaining_files_with_type_length,
        get_actual_token_counts=lambda:
        (int(findall('.*\s+(\d+) received.*',self.coder.usage_report)[0]) if hasattr(self.coder,"usage_report") else 0 ,
        int(findall('.*\s+(\d+)k sent.*',self.coder.usage_report)[0]) if hasattr(self.coder,"usage_report") else 0)):
            self.coder.abs_fnames = set([f[0] for f in files_to_send_with_types if f[1]])
            self.coder.abs_read_only_fnames = set(f[0] for f in files_to_send_with_types if not f[1])
            self.coder.run_one(user_message,preproc)
    class file_cruncher:
            total_input_tokens:int
            total_output_tokens:int = 0
            max_context:int
            max_output:int
            remaining_files : list[Tuple[str,bool,int]]
            get_actual_token_count :Callable[[],Tuple[int,int]]
            PADDING:int = 50
            def __init__(self,max_context:int,max_output:int,chat_history_tokens,remaining_files : list[Tuple[str,bool,int]], get_actual_token_counts :Callable[[],int]  ):
                self.total_input_tokens = chat_history_tokens
                
                self.remaining_files = remaining_files
                self.max_context = max_context
                self.max_output = max_output
                self.get_actual_token_count = get_actual_token_counts
                self.remaining_files = sorted(remaining_files, key = lambda x: x[2])
            def __iter__(self):
                return self        
            def __next__(self):
                if len(self.remaining_files) == 0:
                    raise StopIteration
                sent,received = self.get_actual_token_count()
                self.total_input_tokens += sent
                self.total_output_tokens += received
                files_to_send : list[Tuple[str,bool]]= []
                i:int =0
                for t in self.remaining_files:
                    file_name,type_,length = t
                    if length + (length + self.PADDING) + self.total_input_tokens >= self.max_context or length + self.PADDING + self.total_output_tokens  >= self.max_output:
                        break
                    files_to_send.append((file_name,type_))
                    i+=1
                if i == 0:
                    raise Exception("No file fits the context and output token limits")
                self.remaining_files = self.remaining_files[i:]
                return files_to_send