#!/usr/bin/env python

# This is a Python script that uses OpenAI's GPT-3 to modify code based on user requests.

import os
import sys
import copy
import random
import json

from pathlib import Path
from collections import defaultdict

import os
import openai

from dump import dump

openai.api_key = os.getenv("OPENAI_API_KEY")

prompt_webdev = '''
I want you to act as a web development pair programmer.
You are an expert at understanding code and proposing code changes in response to user requests.

Ask any questions you need to fully understand the user's request.

DO NOT REPLACE ENTIRE FILES!

YOU MUST ONLY RETURN CODE USING THESE COMMANDS:
  - BEFORE/AFTER
  - DELETE
  - APPEND
  - PREPEND

** This is how to replace lines from a file with a new set of lines.

BEFORE path/to/filename.ext
```
... a series of lines from ...
... the original file ...
... completely unchanged ...
... include ONLY the sections of the file which need changes! ...
... DO NOT USE THIS TO REPLACE AN ENTIRE FILES CONTENTS ...
```
AFTER
```
... all occurances of the before lines ...
... will get replaced with the after lines ...
```

** This is how to remove lines from a file:

DELETE path/to/filename.ext
```
... a series of sequential entire lines from ...
... the original file ...
... completely unchanged ...
... that will be deleted ...
```

** This is how to append lines onto the end of a file:

APPEND path/to/filename.ext
```
... lines to add ...
... at the end of the file ...
```

** This is how to insert lines at the start of a file:

PREPEND path/to/filename.ext
```
... lines to add ...
... at the start of the file ...
```

Study the provided code and then ask the user how they want you to change it.
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


    def get_files_message(self):
        prompt = ''
        for fname in self.fnames:
            prompt += self.quoted_file(fname)
        return prompt

    def run(self):

        messages = [
            dict(role = 'system', content = self.system_prompt),
            dict(role = 'user', content = self.get_files_message()),
        ]
        file_msg_no = 1

        while True:
            content = self.send(messages)
            self.update_files(content)
            inp = input()
            if self.files_modified():
                print('Updating ChatGPT with current file contents')
                messages[file_msg_no] = dict(role = 'user', content = '<<outdated list of the files and their content -- removed>>')
                messages.append(
                    dict(
                        role = 'user',
                        content = 'The files have been updated. Here is the current content of the files. Take note! Base future changes on this update!\n' + self.get_files_message(),
                    )
                )
                file_msg_no = len(messages)-1

            message = dict(role = 'user', content = inp)
            messages.append(message)


    def send(self, messages):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            #model="gpt-4",
            messages=messages,
            temperature=0,
            stream = True,
        )
        resp = []
        for chunk in completion:
            try:
                text = chunk.choices[0].delta.content
                resp.append(text)
            except AttributeError:
                continue
            sys.stdout.write(text)
            sys.stdout.flush()

        print()
        print('='*40)

        resp = ''.join(resp)
        return resp

    quotes = '```'

    def parse_op(self, lines):
        if lines[1] != self.quotes or lines[-1] != self.quotes:
            raise ValueError(lines)

        pieces = lines[0].split()
        cmd = pieces[0]
        if cmd not in ('BEFORE', 'AFTER', 'APPEND'):
            raise ValueError(cmd)

        if len(pieces) > 1:
            fname = pieces[1]
        else:
            if cmd != 'AFTER':
                raise ValueError
            fname = None

        return cmd, fname, lines[2:-1]

    def update_files(self, content):

        lines = content.splitlines()
        line_nums = [i for i, j in enumerate(lines) if j == self.quotes]
        pairs = [(line_nums[i], line_nums[i+1]) for i in range(0, len(line_nums), 2)]

        ops = [
            lines[start-1:end+1]
            for start,end in pairs
        ]
        ops.reverse()
        while ops:
            op = ops.pop()
            cmd,fname,op_lines = self.parse_op(op)
            if cmd == 'BEFORE':
                after_op = ops.pop()
                self.do_before(cmd, fname, op_lines, after_op)
                continue
            if cmd == 'APPEND':
                self.do_append(cmd, fname, op_lines)
                continue

    def do_append(self, cmd, fname, op_lines):
        if fname not in self.fnames:
            raise ValueError(fname)

        fname = Path(fname)
        content = fname.read_text()
        if content[-1] != '\n':
            content += '\n'
        content += '\n'.join(op_lines)
        content += '\n'
        fname.write_text(content)

    def do_before(self, cmd, fname, op_lines, after_op):
        after_cmd,after_fname,after_lines = self.parse_op(after_op)
        if after_cmd != 'AFTER':
            raise ValueError(after_cmd)
        if fname not in self.fnames:
            dump(self.fnames)
            raise ValueError(fname)

        fname = Path(fname)

        content = fname.read_text().splitlines()
        before = [l.strip() for l in op_lines]
        stripped_content = [l.strip() for l in content]
        where = find_index(stripped_content, before)

        if where < 0:
            raise ValueError(before)

        new_content = content[:where]
        new_content += after_lines
        new_content += content[where+len(before):]
        new_content = '\n'.join(new_content) + '\n'

        fname.write_text(new_content)





coder = Coder()

coder.system(prompt_webdev)

for fname in sys.argv[1:]:
    coder.add_file(fname)

#coder.update_files(Path('tmp.commands').read_text()) ; sys.exit()

coder.run()

#dname = Path('../easy-chat')
#coder.file(dname / 'index.html')
#coder.file(dname / 'chat.css')
#coder.file(dname / 'chat.js')

#for fname in coder.fnames:
#    print(coder.quoted_file(fname))
#sys.exit()

'''
Change all the speaker icons to orange.

The speaker icons come before the text of each message. Move them so they come after the text instead.

Move the About and New Chat links into a hamburger menu.
'''
