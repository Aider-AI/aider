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
Make the requested change to the provided code and output the changed code.
MAKE NO OTHER CHANGES!
Do not provide explanations!
'''

class Chat:
    fnames = []
    def system(self, prompt):
        self.system_prompt = prompt
    def file(self, fname):
        self.fnames.append(fname)
    def request(self, prompt):
        self.request_prompt = prompt

    def run(self):
        prompt = self.request_prompt + '\n###\n'

        for fname in self.fnames:
            prompt += '\n'
            prompt += fname.name
            prompt += '\n```\n'
            prompt += fname.read_text()
            prompt += '\n```\n'

        messages = [
            dict(role = 'system', content = self.system_prompt),
            dict(role = 'user', content = prompt),
        ]

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            stream = True
        )
        for chunk in completion:
            try:
                text = chunk.choices[0].delta.content
            except AttributeError:
                continue
            sys.stdout.write(text)
            sys.stdout.flush()


chat = Chat()

chat.system(prompt_webdev)

chat.request('''
Replace *ALL* the speaker icons with a speech bubble icon.
''')

dname = Path('../easy-chat')
chat.file(dname / 'index.html')
chat.file(dname / 'chat.js')
chat.file(dname / 'chat.css')

chat.run()
