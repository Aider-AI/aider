#!/usr/bin/env python

# This is a Python script that uses OpenAI's GPT-3 to modify code based on user requests.

import os
import sys
import copy
import random
import json
import re
import readline
import traceback

from tqdm import tqdm

from pathlib import Path
from collections import defaultdict
from pygments import highlight, lexers, formatters

import os
import openai

from dump import dump

import prompts

history_file = '.coder.history'
try:
    readline.read_history_file(history_file)
except FileNotFoundError:
    pass

formatter = formatters.TerminalFormatter()

openai.api_key = os.getenv("OPENAI_API_KEY")


def find_index(list1, list2):
    for i in range(len(list1)):
        if list1[i:i+len(list2)] == list2:
            return i
    return -1

class Coder:
    fnames = dict()

    def add_file(self, fname):
        self.fnames[fname] = Path(fname).stat().st_mtime

    def files_modified(self):
        for fname,mtime in self.fnames.items():
            if Path(fname).stat().st_mtime != mtime:
                return True

    def request(self, prompt):
        self.request_prompt = prompt

    def quoted_file(self, fname):
        prompt = '\n'
        prompt += fname
        prompt += '\n```\n'
        prompt += Path(fname).read_text()
        prompt += '\n```\n'
        return prompt

    def get_files_content(self):
        prompt = ''
        for fname in self.fnames:
            prompt += self.quoted_file(fname)
        return prompt

    def get_input(self):

        print()
        print('='*60)
        inp = ''
        while not inp.strip():
            try:
                inp = input('> ')
            except EOFError:
                return

        print()

        #readline.add_history(inp)
        readline.write_history_file(history_file)

        return inp

    def run(self):
        messages = [
            dict(role = 'system', content = prompts.main_system),
        ]

        did_edits = False
        while True:
            inp = self.get_input()
            if inp is None:
                return

            if did_edits:
                files_content = prompts.files_content_prefix_edited
            else:
                files_content = prompts.files_content_prefix_plain

            files_content += self.get_files_content()
            files_content += prompts.files_content_suffix

            messages += [
                dict(role = 'user', content = files_content),
                dict(role = 'assistant', content = "Ok."),
                dict(role = 'user', content = inp),
                #dict(role = 'system', content = prompts.system_reminder),
            ]

            content = self.send(messages)
            messages.pop() # system
            messages.pop() # user msg
            messages.pop() # assistant Ok.
            messages.pop() # user files content

            # put back the user message without prompts.user_suffix
            messages.append(dict(role = 'user', content = inp))
            messages.append(dict(role = 'assistant', content = content))

            print()
            print()
            try:
                did_edits = self.update_files(content, inp)
                if did_edits:
                    print()
            except Exception as err:
                print(err)
                print()
                traceback.print_exc()

    def show_messages(self, messages):
        for msg in messages:
            print()
            print('-' * 50)
            role = msg['role'].upper()
            content = msg['content']
            print(f'{role}: {content.strip()}')

    def send(self, messages, show_progress = 0):
        self.show_messages(messages)

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            #model="gpt-4",
            messages=messages,
            temperature=0,
            stream = True,
        )

        if show_progress:
            return self.show_send_progress(completion, show_progress)
        else:
            return self.show_send_output_color(completion)

    def show_send_progress(self, completion, show_progress):
        resp = []
        pbar = tqdm(total = show_progress)
        for chunk in completion:
            try:
                text = chunk.choices[0].delta.content
                resp.append(text)
            except AttributeError:
                continue

            pbar.update(len(text))

        pbar.update(show_progress)
        pbar.close()

        resp = ''.join(resp)
        return resp

    def show_send_output_plain(self, completion):
        resp = []

        in_diff = False
        diff_lines = []

        def print_lines():
            if not diff_lines:
                return
            code = '\n'.join(diff_lines)
            lexer = lexers.guess_lexer(code)
            code = highlight(code, lexer, formatter)
            print(code, end='')

        partial_line = ''
        for chunk in completion:
            try:
                text = chunk.choices[0].delta.content
                resp.append(text)
            except AttributeError:
                continue

            sys.stdout.write(text)
            sys.stdout.flush()

        return ''.join(resp)

    def show_send_output_color(self, completion):
        resp = []

        in_diff = False
        diff_lines = []

        def print_lines():
            if not diff_lines:
                return
            code = '\n'.join(diff_lines)
            lexer = lexers.guess_lexer(code)
            code = highlight(code, lexer, formatter)
            print(code, end='')

        partial_line = ''
        for chunk in completion:
            try:
                text = chunk.choices[0].delta.content
                resp.append(text)
            except AttributeError:
                continue

            lines = (partial_line + text)
            lines = lines.split('\n')
            partial_line = lines.pop()

            for line in lines:
                check = line.rstrip()
                if check == '>>>>>>> UPDATED':
                    print_lines()
                    in_diff = False
                    diff_lines = []

                if check == '=======':
                    print_lines()
                    diff_lines = []
                    print(line)
                elif in_diff:
                    diff_lines.append(line)
                else:
                    print(line)

                if line.strip() == '<<<<<<< ORIGINAL':
                    in_diff = True
                    diff_lines = []

        print_lines()
        if partial_line:
            print(partial_line)

        return ''.join(resp)


    pattern = re.compile(r'^(\S+)\n<<<<<<< ORIGINAL\n(.*?)\n=======\n(.*?)\n>>>>>>> UPDATED$', re.MULTILINE | re.DOTALL)

    def update_files(self, content, inp):
        did_edits = False

        for match in self.pattern.finditer(content):
            did_edits = True
            path, original, updated = match.groups()
            if self.do_replace(path, original, updated):
                continue
            edit = match.group()
            self.do_gpt_powered_replace(path, edit, inp)

        return did_edits

    def do_replace(self, fname, before_text, after_text):
        before_text = self.strip_quoted_wrapping(before_text, fname)
        after_text = self.strip_quoted_wrapping(after_text, fname)

        fname = Path(fname)
        content = fname.read_text().splitlines()
        before_lines = [l.strip() for l in before_text.splitlines()]
        stripped_content = [l.strip() for l in content]
        where = find_index(stripped_content, before_lines)

        if where < 0:
            return

        new_content = content[:where]
        new_content += after_text.splitlines()
        new_content += content[where+len(before_lines):]
        new_content = '\n'.join(new_content) + '\n'

        fname.write_text(new_content)
        print('Applied edit to', fname)
        return True

    def do_gpt_powered_replace(self, fname, edit, request):
        print(f'Asking GPT to apply ambiguous edit to {fname}...')

        fname = Path(fname)
        content = fname.read_text()
        prompt = prompts.editor_user.format(
            request = request,
            edit = edit,
            fname = fname,
            content = content,
            )

        messages = [
            dict(role = 'system', content = prompts.editor_system),
            dict(role = 'user', content = prompt),
        ]
        res = self.send(messages, show_progress = len(content) + len(edit)/2)
        res = self.strip_quoted_wrapping(res, fname)
        fname.write_text(res)

    def strip_quoted_wrapping(self, res, fname=None):
        if not res:
            return res

        res = res.splitlines()

        if fname and res[0].strip().endswith(Path(fname).name):
            res = res[1:]

        if res[0].startswith('```') and res[-1].startswith('```'):
            res = res[1:-1]

        res = '\n'.join(res)
        if res and res[-1] != '\n':
            res += '\n'

        return res

coder = Coder()

for fname in sys.argv[1:]:
    coder.add_file(fname)

#coder.update_files(Path('tmp.commands').read_text()) ; sys.exit()

coder.run()
