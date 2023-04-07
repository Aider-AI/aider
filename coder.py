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
I want you to act as a web development pair programmer.
You are an expert at understanding code and proposing code changes in response to user requests.
Study the provided code and then change it according to the user's requests.

BEFORE YOU MAKE CHANGES TO THE CODE ASK ANY QUESTIONS YOU NEED TO UNDERSTAND THE USER'S REQUEST.
ASK QUESTIONS IF YOU NEED HELP UNDERSTANDING THE CODE.
Ask all the questions you need to fully understand what needs to be done.

ONLY RETURN CODE USING THESE COMMANDS:
  - CHANGE
  - DELETE
  - APPEND

** This is how to use the CHANGE command:

CHANGE filename.ext
BEFORE
```
... a series of lines from ...
... the original file ...
... completely unchanged ...
... include only the sections of the file which need changes! ...
... don't include the entire before file! ...
```
AFTER
```
... the lines to replace them with ...
```

** This is how to use the DELETE command:

DELETE filename.ext
```
... a series of sequential entire lines from ...
... the original file ...
... completely unchanged ...
... that will be deleted ...
```

** This is how to use the APPEND command:

APPEND filename.ext APPEND
```
... lines to add ...
... at the end of the file ...
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



    def run(self):
        prompt = ''

        #prompt += self.request_prompt
        #prompt += '\n###\n'

        for fname in self.fnames:
            prompt += self.quoted_file(fname)

        messages = [
            dict(role = 'system', content = self.system_prompt),
            dict(role = 'user', content = prompt),
        ]

        while True:
            content = self.send(messages)
            inp = input()
            inp += '\n(Remember if you want to output code, be sure to a correctly formatted CHANGE, DELETE, APPEND command)'
            message = dict(role = 'user', content = inp)
            messages.append(message)

        self.update_files(content)

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

    def update_files(self, content):
        for fname in self.fnames:
            self.update_file(fname, content)

    def update_file(self, fname, content):
        start = f'{fname.name}\n```\n'
        end = '\n```'

        if start not in content:
            print(f'{fname} no updates')
            return

        print(f'{fname} updated')
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

#coder.request('''
#Change all the speaker icons to orange.
#''')

#coder.request('''
#The speaker icons come before the text of each message.
#Move them so they come after the text instead.
#''')

#coder.request('''
#Move the About and New Chat links into a hamburger menu.
#''')

coder.run()
