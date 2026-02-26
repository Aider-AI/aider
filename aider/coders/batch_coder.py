from typing import Tuple, override
import copy

from aider.coders.base_coder import Coder
from aider.coders.base_prompts import CoderPrompts
"""Perform a coding task on multiple files in batches that fit the context and outpot token limits, without sending them all at once."""
class BatchCoder(Coder):
    coder : Coder = None
    original_kwargs: dict = None
    edit_format = "batch"
                        
    def __init__(self, main_model, io, **kwargs):
        super().__init__(main_model, io,**kwargs)
        if 'gpt_prompts' not in kwargs: self.gpt_prompts = CoderPrompts()
    @override
    def run_one(self, user_message, preproc):
        if self.coder is None:
            self.coder = Coder.create(main_model=self.main_model, edit_format=self.main_model.edit_format,from_coder=self,**self.original_kwargs)
            self.coder.auto_lint, self.coder.auto_commits = (False,False)
        chat_files_with_type_and_length = self.get_chat_files_with_type_and_length()
        max_tokens = self.main_model.info.get('max_tokens')
        max_context = self.main_model.info['max_input_tokens']
        max_output = max_tokens if max_tokens is not None else self.main_model.info['max_output_tokens']
        repo_token_count = self.main_model.get_repo_map_tokens()
        history_token_count = sum([tup[0] for tup in self.summarizer.tokenize( [msg["content"] for msg in self.done_messages])])
        prev_io= self.io.yes #shell commmands will still need confirmation for each command, this can be overridden by extending InputOutput class and overriding confirm_ask method.
        self.io.yes = True
        cruncher = self.file_cruncher( max_context, max_output,repo_token_count + history_token_count, 
                                      chat_files_with_type_and_length)
        edited_files = self.batch_process(user_message,preproc, cruncher)
        self.io.yes= prev_io
        if len(edited_files) == 0: return
        if self.auto_lint:
            cruncher.files_to_crunch = [(fname,True,self.main_model.token_count(self.io.read_text(fname))) for fname in edited_files]
            self.batch_lint(cruncher,preproc)
        if self.auto_commits:
            self.batch_commit(edited_files)

    def get_chat_files_with_type_and_length(self):
        chat_files_with_type_and_length : list[Tuple[str,bool,int]]=[]
        for f in self.abs_fnames:
                chat_files_with_type_and_length.append((f, True, self.main_model.token_count(self.io.read_text(f))))
        for f in self.abs_read_only_fnames:
                chat_files_with_type_and_length.append((f,False,self.main_model.token_count(self.io.read_text(f))))
        return chat_files_with_type_and_length
        
    def batch_process(self,message,preproc, cruncher):
        edited_files= []
        for files_to_send_with_types in cruncher:
            self.prepare_batch(files_to_send_with_types)
            self.coder.run_one(message,preproc)
            edited_files.extend(self.coder.aider_edited_files)
            self.coder.aider_edited_files = set()
        return edited_files
    
    def prepare_batch(self,files_to_send_with_types : list[Tuple[str,bool]]):
        self.coder.done_messages = copy.deepcopy(self.done_messages)
        self.coder.cur_messages = []
        self.coder.abs_fnames=set([f[0] for f in files_to_send_with_types if f[1]])
        self.coder.abs_read_only_fnames=set(f[0] for f in files_to_send_with_types if not f[1])
    def batch_lint(self, cruncher,preproc):
        for files_with_type in cruncher:
            files = [ft[0] for ft in files_with_type]
            lint_msg =  self.coder.lint_edited(files)
            self.auto_commit(files,context="Ran the linter")
            if lint_msg:
                ok = self.io.confirm_ask("Attempt to fix lint errors?", subject="batch_lint", allow_never=True)
                if ok:
                    self.coder.done_messages, self.coder.cur_messages = ([],[])
                    self.coder.run_one(lint_msg,preproc)
    def batch_commit(self, files : list[str]):
        self.repo.commit(files)
         
    class file_cruncher:
            context_tokens: int
            max_context:int
            max_output:int
            files_to_crunch : list[Tuple[str,bool,int]]
            PADDING:int = 50
            def __init__(self,max_context:int,max_output:int,context_tokens,files_to_crunch : list[Tuple[str,bool,int]]  ):
                self.context_tokens = context_tokens
                self.max_context = max_context
                self.max_output = max_output
                self.files_to_crunch = sorted(files_to_crunch, key = lambda x: x[2])
            def __iter__(self):
                return self      
            """fitting input files + chat history + repo_map + files_to_send to context limit and
            files_to_send to the output limit.
            output files are assumed to be half the size of input files"""            
            def __next__(self):
                if len(self.files_to_crunch) == 0:
                    raise StopIteration
                files_to_send : list[Tuple[str,bool]]= []
                i:int =0
                total_context= 0
                total_output= 0
                for file_name, type_, length in self.files_to_crunch:
                    if length + length / 2 + self.context_tokens + total_context>= self.max_context or length / 2 + total_output  >= self.max_output:
                        break
                    total_context+=length + length + self.PADDING
                    total_output+=length + self.PADDING
                    files_to_send.append((file_name,type_))
                    i+=1
                if i == 0: #no file fits the limits, roll the dice and let the user deal with it
                    f,t,_ = self.files_to_crunch[i]
                    files_to_send.append((copy.copy(f), t))
                    i=1
                self.files_to_crunch = self.files_to_crunch[i:]
                return files_to_send
        
