#!/usr/bin/env python

# This is a Python script that uses OpenAI's GPT-3 to modify code based on user requests.

import os
import sys
import copy
import random
import json
import re
import readline
from tqdm import tqdm

from pathlib import Path
from collections import defaultdict

import os
import openai

from dump import dump

history_file = '.coder.history'
try:
    readline.read_history_file(history_file)
except FileNotFoundError:
    pass

openai.api_key = os.getenv("OPENAI_API_KEY")

prompt_webdev = '''
I want you to act as an expert software engineer and pair programmer.
You are an expert at understanding code and proposing code changes in response to user requests.

Your job is to:
  - Understand what the user wants. Ask questions if needed.
  - Suggest changes to the code.

FOR EACH CHANGE TO THE CODE, DESCRIBE IT USING THIS FORMAT:

path/to/filename.ext
<<<<<<< ORIGINAL
a chunk of the **exact** lines
from the original file
that needs to be changed
=======
new lines to replace
the original chunk
>>>>>>> UPDATED

ONLY USE THIS ORIGINAL/UPDATED FORMAT TO DESCRIBE CODE CHANGES!
'''

prompt_comments = '''
I want you to act as a web development expert.
I want you to answer only with comments in the code.
Whatever the user requests, add comments in the code showing how to make the requested change and explaining why it will work.
Just add comments to the code.
Output the new version of the code with added comments.
Embed lots of comments in the code explaining how and where to make changes.
MAKE NO OTHER CHANGES!

For each file, output like this:

path/to/filename.ext
```
... file content ...
```
'''


def find_index(list1, list2):
    for i in range(len(list1)):
        if list1[i:i+len(list2)] == list2:
            return i
    return -1

class Coder:
    fnames = dict()

    def system(self, prompt):
        self.system_prompt = prompt

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

    def run_davinci(self):
        prompt = ''
        prompt += 'Original code:\n\n'

        for fname in self.fnames:
            prompt += self.quoted_file(fname)

        prompt += '\n###\n'
        prompt += self.request_prompt

        prompt += '\n###\n'

        prompt += 'Modified code including those changes:\n\n'

        completion = openai.Completion.create(
            model="text-davinci-003",
            prompt= prompt,
            max_tokens=2048,
            temperature=0,
            stream = True,
        )
        resp = ''
        for chunk in completion:
            try:
                text = chunk.choices[0].text
                resp += text
            except AttributeError:
                continue

            sys.stdout.write(text)
            sys.stdout.flush()

        resp = ''.join(resp)
        self.update_files(resp)


    def run_edit(self):
        prompt = ''
        for fname in self.fnames:
            prompt += self.quoted_file(fname)

        completion = openai.Edit.create(
            model="code-davinci-edit-001",
            instruction= prompt,
            input=prompt,
            #max_tokens=2048,
            temperature=0,
        )
        dump(completion)
        resp = []
        for chunk in completion:
            try:
                text = chunk.choices[0].text
                resp.append(text)
            except AttributeError:
                continue
            sys.stdout.write(text)
            sys.stdout.flush()

        resp = ''.join(resp)
        self.update_files(resp)


    def get_files_content(self):
        prompt = ''
        for fname in self.fnames:
            prompt += self.quoted_file(fname)
        prompt += '\n\nRemember, NEVER REPLY WITH WHOLE FILES LIKE THIS. ONLY TELL ME CODE CHANGES USING ORIGINAL/UPDATED EDIT COMMANDS!\n'
        return prompt

    change_notice = '''
TAKE NOTE!
The contents of the files have been updated!
USE THESE FILES NOW.
MAKE ANY CHANGES BASED OFF THESE FILES!
'''
    def get_input(self):

        print()
        print('='*60)
        inp = input('> ')
        print()

        #readline.add_history(inp)
        readline.write_history_file(history_file)

        return inp

    def run(self):
        messages = [
            dict(role = 'system', content = self.system_prompt),
        ]

        did_edits = False
        while True:
            inp = self.get_input()

            if did_edits:
                files_prefix = 'I made your suggested changes, here are the updated files:'
            else:
                files_prefix = 'Here are the files:'
            files_prefix += '\n\n'


            messages += [
                dict(role = 'user', content = files_prefix + self.get_files_content()),
                dict(role = 'assistant', content = "Ok."),
                dict(role = 'user', content = inp),
            ]

            content = self.send(messages)
            user_msg = messages.pop()
            messages.pop()
            messages.pop()
            messages.append(user_msg)
            messages.append(dict(role = 'assistant', content = content))

            print()
            print()
            try:
                did_edits = self.update_files(content)
                if did_edits:
                    print()
            except Exception as err:
                print(err)
                print()

    def send(self, messages, show_progress = 0):
        #for msg in messages:
        #    dump(msg)

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            #model="gpt-4",
            messages=messages,
            temperature=0,
            stream = True,
        )
        resp = []

        if show_progress:
            pbar = tqdm(total = show_progress)

        for chunk in completion:
            try:
                text = chunk.choices[0].delta.content
                resp.append(text)
            except AttributeError:
                continue
            if show_progress:
                pbar.update(len(text))
            else:
                sys.stdout.write(text)
                sys.stdout.flush()

        if show_progress:
            pbar.update(show_progress)
            pbar.close()

        resp = ''.join(resp)
        return resp


    pattern = re.compile(r'^(\S+)\n<<<<<<< ORIGINAL\n(.+?)\n=======\n(.+?)\n>>>>>>> UPDATED$', re.MULTILINE | re.DOTALL)

    def update_files(self, content):
        did_edits = False

        for match in self.pattern.finditer(content):
            did_edits = True
            path, original, updated = match.groups()
            if self.do_replace(path, original, updated):
                continue
            edit = match.group()
            self.do_gpt_powered_replace(path, edit)

        return did_edits

    def do_replace(self, fname, before_text, after_text):
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

    def do_gpt_powered_replace(self, fname, edit):
        print(f'Asking GPT to apply ambiguous edit to {fname}...')
        fname = Path(fname)
        content = fname.read_text()
        prompt = f'''
Apply this change:

{edit}

To this file:

{fname}
```
{content}
```
'''
        sys_prompt = '''
You are an expert code editor.
Perform the requested edit.
Output ONLY the new version of the file.
Do not output explanations!
Do not wrap the output in ``` delimiters.
Just the content of the file!
'''

        messages = [
            dict(role = 'system', content = sys_prompt),
            dict(role = 'user', content = prompt),
        ]
        res = self.send(messages, show_progress = len(content) + len(edit)/2)

        res = res.splitlines()
        if res[0].strip == str(fname):
            res = res[1:]
        if res[0].strip() == '```' and res[-1].strip() == '```':
            res = res[1:-1]

        res = '\n'.join(res)
        if res[-1] != '\n':
            res += '\n'
        fname.write_text(res)


def test_do_gpt_powered_replace(coder):
    fname = Path('../easy-chat/index.html')
    edit = '''
../easy-chat/index.html
<<<<<<< ORIGINAL
<p class="user"><span class="fa fa-volume-up" onclick="speak(this.parentNode)"></span><span>Hello!</span></p>
<p class="assistant"><span class="fa fa-volume-up" onclick="speak(this.parentNode)"></span><span>How</span> <span>can</span> <span>I</span> <span>help</span>
    <span>you?</span></p>
=======
<p class="user"><span>Hello!</span><span class="fa fa-volume-up" onclick="speak(this.parentNode)"></span></p>
<p class="assistant"><span>How</span> <span>can</span> <span>I</span> <span>help</span><span>you?</span><span class="fa fa-volume-up" onclick="speak(this.parentNode)"></span></p>
>>>>>>> UPDATED
'''
    coder.do_gpt_powered_replace(fname, edit)

coder = Coder()
#test_do_gpt_powered_replace(coder) ; sys.exit()

coder.system(prompt_webdev)
for fname in sys.argv[1:]:
    coder.add_file(fname)

#coder.update_files(Path('tmp.commands').read_text()) ; sys.exit()

coder.run()

'''
Change all the speaker icons to orange.

Currently the speaker icons come before the text of each message. Move them so they come after the text instead.

Move the About and New Chat links into a hamburger menu.
'''
