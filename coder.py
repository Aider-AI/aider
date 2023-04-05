#!/usr/bin/env python

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
I want you to act as a web development expert.
I want you to answer only with code.
Make all the requested changes to the provided code and output the changed code.
MAKE NO OTHER CHANGES!
Do not provide explanations!

For each file that has changes, output it like this:

filename.ext
```
... file content ...
```
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

filename.ext
```
... file content ...
```
'''

class Coder:
    fnames = []
    def system(self, prompt):
        self.system_prompt = prompt
    def file(self, fname):
        self.fnames.append(fname)
    def request(self, prompt):
        self.request_prompt = prompt

    def quoted_file(self, fname):
        prompt = '\n'
        prompt += fname.name
        prompt += '\n```\n'
        prompt += fname.read_text()
        prompt += '\n```\n'
        return prompt

    def run(self):
        prompt = ''
        for fname in self.fnames:
            prompt += self.quoted_file(fname)

        prompt += '\n###\n'
        prompt += self.request_prompt

        messages = [
            dict(role = 'system', content = self.system_prompt),
            dict(role = 'user', content = prompt),
        ]

        content = self.send(messages)
        self.update_files(content)

    def send(self, messages):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
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

    def update_files(self, content):
        for fname in self.fnames:
            dump(fname)
            self.update_file(fname, content)

    def update_file(self, fname, content):
        start = f'{fname.name}\n```\n'
        end = '\n```'

        if start not in content:
            print(f'No content for {fname}')
            return

        content = content.split(start)[1]
        content = content.split(end)[0]

        fname.write_text(content)

coder = Coder()

coder.system(prompt_webdev)

dname = Path('../easy-chat')
coder.file(dname / 'index.html')
coder.file(dname / 'chat.css')
coder.file(dname / 'chat.js')

#for fname in coder.fnames:
#    print(coder.quoted_file(fname))
#sys.exit()

coder.request('''
Refactor the css and remove any redundant or useless code.
''')

coder.run()
