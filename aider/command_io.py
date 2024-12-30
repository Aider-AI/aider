import sys
import json
import select
import re

from aider.io import InputOutput
from aider.io import AutoCompleter
from aider.mdstream import MarkdownStream
from prompt_toolkit.document import Document

class CommandMarkdownStream(MarkdownStream):
    def __init__(self):
        super().__init__()
        self.last_position = 0

    def update(self, text, final=False):
        new_text = text[self.last_position:]
        if new_text or final:
            msg = {
                "cmd": "assistant-stream",
                "value": new_text,
                "position": self.last_position,
                "final": final
            }        
            print(json.dumps(msg), flush=True)
        self.last_position = len(text)
        return

class CommandIO(InputOutput):
    def __init__(
        self,
        yes=False,
        input_history_file=None,
        chat_history_file=None,
        encoding="utf-8",
        dry_run=False,
        llm_history_file=None
    ):
        super().__init__(
            input_history_file=input_history_file,
            chat_history_file=chat_history_file,
            encoding=encoding,
            dry_run=dry_run,
            llm_history_file=llm_history_file,
        )

        self.edit_format:str = "whole"
        self.yes = yes
        self.input_buffer = ""
        self.input_decoder = json.JSONDecoder()
        self.updated_rel_fnames = None
        self.updated_abs_read_only_fnames = None

    def set_edit_format(self, edit_format):
        self.edit_format = edit_format
        
    def update_files(self, rel_fnames, abs_read_only_fnames):
        if(rel_fnames == self.updated_rel_fnames and abs_read_only_fnames == self.updated_abs_read_only_fnames):
            return
        
        msg = {
            'added': list(rel_fnames),
            'added_readonly': list(abs_read_only_fnames)
        }
        print(f"update_files: {msg}")
        self.send_message('files', msg, False)
        
        self.updated_rel_fnames = rel_fnames
        self.updated_abs_read_only_fnames = abs_read_only_fnames
        
    def get_input(
        self,
        root,
        rel_fnames,
        addable_rel_fnames,
        commands,
        abs_read_only_fnames=None,
        edit_format=None
    ):
        self.update_files(rel_fnames, abs_read_only_fnames)
        
        obj = self.get_command()
        
        completer_instance = AutoCompleter(
            root,
            rel_fnames,
            addable_rel_fnames,
            commands,
            self.encoding,
            abs_read_only_fnames=abs_read_only_fnames,
        )
        
        if obj:
            send, inp = self.run_command(obj, commands, completer_instance)

            if send:
                return inp
        
        return ""
    
    def get_command(self, wait = True):
        need_input = False
        
        while True:
            try:
                input_chunk = sys.stdin.readline()
                
#                print(f"read: {input_chunk}", flush=True)
                if not input_chunk and need_input:
                    if wait:
                        select.select([sys.stdin], [], [], 1)
                    else:
                        return None
                    
                if input_chunk:
                    self.input_buffer += input_chunk

                while self.input_buffer:
                    try:
                        obj, idx = self.input_decoder.raw_decode(self.input_buffer)
                        self.input_buffer = self.input_buffer[idx:].lstrip()
                        return obj
                        
                    except json.JSONDecodeError as e:
                        # If JSON is not complete, break
                        print(f"json not complete: {e.msg}", flush=True)
                        need_input = True
                        self.input_buffer.clear()
                        break

            except KeyboardInterrupt:
                break
        
        return ""
    
    def run_command(self, obj, commands, completer_instance):
        cmd_list = commands.get_commands()
        
        cmd = obj.get('cmd')
        
        if cmd in cmd_list:
            return True, f"{cmd} {obj.get('value')}"
        elif cmd == 'interactive':
            text = obj.get('value', '')
            cursor_position = len(text)
            
            document = Document(text, cursor_position=cursor_position)
            completions = list(completer_instance.get_completions(document, None))
            
            suggestions = []
            for completion in completions:
                suggestion = {
                    'text': completion.text,
                    'display': completion.display or completion.text,
                    'start_position': completion.start_position,
                    'style': completion.style,
                    'selected_style': completion.selected_style
                }
                suggestions.append(suggestion)
            
            self.send_message('auto_complete', suggestions, False)
            return False, ""
        elif cmd == 'user':
            return True, obj.get('value')
        return False, ""
        
    def user_input(self, inp, log_only=True):
        self.send_message("user", inp)
        return

    def ai_output(self, content):
        hist = "\n" + content.strip() + "\n\n"
        self.append_chat_history(hist)
#        self.send_message("ai", content)
        
    def confirm_ask(
        self,
        question,
        default="y",
        subject=None,
        explicit_yes_required=False,
        group=None,
        allow_never=False,
    ):
        self.num_user_asks += 1

        question_id = (question, subject)

        if question_id in self.never_prompts:
            return False

        if group and not group.show_group:
            group = None
        if group:
            allow_never = True

        valid_responses = ["yes", "no"]
        options = " (Y)es/(N)o"
        if group:
            if not explicit_yes_required:
                options += "/(A)ll"
                valid_responses.append("all")
            options += "/(S)kip all"
            valid_responses.append("skip")
        if allow_never:
            options += "/(D)on't ask again"
            valid_responses.append("don't")

        msg = {
            "cmd": "prompt",
            "value": question,
            "default": default,
            "subject": subject,
            "explicit_yes_required": explicit_yes_required,
            "group": valid_responses,
            "allow_never": allow_never
        }
        print(json.dumps(msg), flush=True)
        
        obj = self.get_command()
        
        cmd = obj.get('cmd')
        res = "no"
        
        if cmd == "prompt_response":
            res = obj.get('value')

        hist = f"{question.strip()} {res.strip()}"
        self.append_chat_history(hist, linebreak=True, blockquote=True)
                
        return res.strip().lower().startswith("y")

    def prompt_ask(self, question, default="", subject=None):
        res = self.confirm_ask(question, default)
    
    def _tool_message(self, type, message="", strip=True):
        if message.strip():
            if "\n" in message:
                for line in message.splitlines():
                    self.append_chat_history(line, linebreak=True, blockquote=True, strip=strip)
            else:
                hist = message.strip() if strip else message
                self.append_chat_history(hist, linebreak=True, blockquote=True)

        if not message:
            return
                       
        self.send_message(type, message)
        
    def tool_error(self, message="", strip=True):
        self.num_error_outputs += 1
        self._tool_message("error", message, strip)

    def tool_warning(self, message="", strip=True):
        self._tool_message("warning", message, strip)
        
    def send_message(self, type, message, escape=True):
        if escape:
            message = json.dumps(message)[1:-1]
        msg = {
            "cmd": type,
            "value": message
        }
        print(json.dumps(msg), flush=True)
       
    def parse_tokens_cost(self, message):                                                                                                                                                                 
        # Match the tokens pattern                                                                                                                                                                  
        tokens_pattern = r'(\d+) sent, (\d+) received'                                                                                                                                              
        tokens_match = re.search(tokens_pattern, message)                                                                                                                                           
                                                                                                                                                                                                    
        # Match the cost pattern                                                                                                                                                                    
        cost_pattern = r'\$(\d+\.\d+) message, \$(\d+\.\d+) session'                                                                                                                                
        cost_match = re.search(cost_pattern, message)                                                                                                                                               
                                                                                                                                                                                                    
        if tokens_match and cost_match:                                                                                                                                                             
            sent = int(tokens_match.group(1))                                                                                                                                                       
            received = int(tokens_match.group(2))                                                                                                                                                   
            cost = float(cost_match.group(1))                                                                                                                                                       
            cost_session = float(cost_match.group(2))                                                                                                                                               
                                                                                                                                                                                                    
            return {
                'sent': sent,
                'received': received,
                'cost': cost,
                'cost_session': cost_session 
            }

        return None
                      
    def check_for_info(self, message):
        pattern = r"Aider v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:\.(?P<build>[^\s]+))?"
        match = re.search(pattern, message)
        
        if match:
            version_info = match.groupdict()
            self.send_message("version", version_info, False)
            return True

        output_parse_map = [
            ("Main model:", "model", None),
            ("Weak model:", "weak_model", None),
            ("Git repo:", "repo", None),
            ("Repo-map:", "repo_map", None),
            ("Tokens:", "tokens", self.parse_tokens_cost)
        ]
        
        for prefix, response_prefix, parser in output_parse_map:
            if message.startswith(prefix):
                remainder = message[len(prefix):].strip()
                value = parser(remainder) if parser else remainder  
                self.send_message(response_prefix, value, False if parser else True)
                return True
        return False
    
    def tool_output(self, *messages, log_only=False, bold=False):
        message=" ".join(messages)
        
        if not message:
            return
        
        if messages:
            hist = message
            hist = f"{hist.strip()}"
            self.append_chat_history(hist, linebreak=True, blockquote=True)
            
        if self.check_for_info(message):
            return
        
        self.send_message("output", message)
        
    def get_assistant_mdstream(self):
        mdStream = CommandMarkdownStream()
        return mdStream
    
    def assistant_output(self, message, pretty=None):
        if not message:
            return
        self.send_message("assistant", message)
        
    def print(self, message=""):
        if not message:
            return
        
        self.send_message("print", message)
