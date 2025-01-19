from typing import Tuple
import copy

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
            self.coder = Coder.create(main_model=self.main_model, edit_format=self.main_model.edit_format,from_coder=self,**self.original_kwargs)
        remaining_files_with_type_length : list[Tuple[str,bool,int]]=[]
        for f in self.abs_fnames:
                remaining_files_with_type_length.append((f, True, self.main_model.token_count(self.io.read_text(f))))
        for f in self.abs_read_only_fnames:
                remaining_files_with_type_length.append((f,False,self.main_model.token_count(self.io.read_text(f))))
        max_tokens = self.main_model.info.get('max_tokens')
        max_context = self.main_model.info['max_input_tokens']
        max_output = self.main_model.info['max_output_tokens']
        repo_token_count = self.main_model.get_repo_map_tokens()
        history_token_count = sum([tup[0] for tup in self.summarizer.tokenize( [msg["content"] for msg in self.done_messages])])
        """fitting input files + chat history + repo_map + files_to_send to context limit and
        files_to_send to the output limit.
        output files are assumed to be greater in size than the input files"""
        for files_to_send_with_types in self.file_cruncher( max_context=max_context,
        max_output= max_tokens if max_tokens is not None else max_output,
        context_tokens=repo_token_count + history_token_count,remaining_files=remaining_files_with_type_length):
            self.coder.done_messages=copy.deepcopy(self.done_messages) #reset history of the coder to the start of the /iterate command
            self.coder.cur_messages=[]
            self.coder.abs_fnames=set([f[0] for f in files_to_send_with_types if f[1]])
            self.coder.abs_read_only_fnames=set(f[0] for f in files_to_send_with_types if not f[1])
            self.coder.run_one(user_message,preproc)
    class file_cruncher:
            context_tokens: int
            max_context:int
            max_output:int
            remaining_files : list[Tuple[str,bool,int]]
            PADDING:int = 50
            def __init__(self,max_context:int,max_output:int,context_tokens,remaining_files : list[Tuple[str,bool,int]]  ):
                self.context_tokens = context_tokens
                self.max_context = max_context
                self.max_output = max_output
                self.remaining_files = sorted(remaining_files, key = lambda x: x[2])
            def __iter__(self):
                return self        
            def __next__(self):
                if len(self.remaining_files) == 0:
                    raise StopIteration
                files_to_send : list[Tuple[str,bool]]= []
                i:int =0
                total_context= 0
                total_output= 0
                for file_name, type_, length in self.remaining_files:
                    if length + (length + self.PADDING) + self.context_tokens + total_context>= self.max_context or length + self.PADDING + total_output  >= self.max_output:
                        break
                    total_context+=length + length + self.PADDING
                    total_output+=length + self.PADDING
                    files_to_send.append((file_name,type_))
                    i+=1
                if i == 0: #no file fits the limits, roll the dice and let the user deal with it
                    f,t,_ = self.remaining_files[i]
                    files_to_send.append((f,t))
                    i=1
                self.remaining_files = self.remaining_files[i:]
                return files_to_send
        