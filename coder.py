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
You are to carefully study the provided code and follow the user instructions.
Be detail oriented, explicit and thorough in following user instructions.
'''

class Chat:
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

    def plan(self):
        self.plan_prompt = '''
Briefly describe all the code changes needed to complete the user request.
Think carefully about the code and the request!
Just describe ALL the changes needed to complete the request.
Just describe the changes, don't output code for them.
Be thorough. Describe ALL the changes needed to complete the request.
Only describe changes related to the request.
Don't output the changed code!
Just briefly describe the changes.

Request:
'''
        prompt = self.plan_prompt
        prompt += self.request_prompt + '\n###\n'

        for fname in self.fnames:
            prompt += self.quoted_file(fname)

        ###
        #print(self.system_prompt)
        #print(prompt)
        #sys.exit()

        self.messages = [
            dict(role = 'system', content = self.system_prompt),
            dict(role = 'user', content = prompt),
        ]
        self.plan = self.send(self.messages)
        self.messages.append(dict(role = 'assistant', content = self.plan))

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

    def update_files(self):
        for fname in self.fnames:
            self.update_file(fname)

    def update_file(self, fname):
        prompt = self.plan_prompt
        prompt += self.request_prompt + '\n###\n'
        prompt += self.quoted_file(fname)

        messages = [
            dict(role = 'system', content = self.system_prompt),
            dict(role = 'user', content = prompt),
            dict(role = 'assistant', content = self.plan),
            dict(role = 'user',
                 content = f'''
Make the requested changes to {fname.name} and output the changed code.
MAKE NO OTHER CHANGES!
JUST OUTPUT CODE.
NO EXPLANATIONS.
'''
            )
        ]
        dump(messages)

        new_content = chat.send(messages)
        if new_content.startswith('```\n'):
            new_content = new_content[4:]
        if new_content.endswith('```\n'):
            new_content = new_content[:-4]
        fname.write_text(new_content)

chat = Chat()

chat.system(prompt_webdev)

dname = Path('../easy-chat')
chat.file(dname / 'index.html')
chat.file(dname / 'chat.css')
chat.file(dname / 'chat.js')

chat.request('Change ALL the speaker icons to speech bubble icons.')

chat.plan()

chat.update_files()
