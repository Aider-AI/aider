#!/usr/bin/env python

# This is a Python script that uses OpenAI's GPT-3 to modify code based on user requests.

import os
import sys
import copy
import random
import json
import re

from pathlib import Path
from collections import defaultdict

import os
import openai

from dump import dump

openai.api_key = os.getenv("OPENAI_API_KEY")

prompt_webdev = '''
I want you to act as a web development pair programmer.
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

NEVER REPLY WITH AN ENTIRE FILE!
ONLY USE THE ABOVE ORIGINAL/UPDATED FORMAT TO DESCRIBE CODE CHANGES!
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
        prompt = 'Here are the files. NEVER USE THIS FORMAT FOR OUTPUT!\n'
        for fname in self.fnames:
            prompt += self.quoted_file(fname)
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
        sys.stdout.write('> ')
        sys.stdout.flush()
        inp = input()
        print()

        if inp == 'fix':
            inp = '''
It looks like you are trying to specify code changes. Repeat your previous message, but use the exact BEFORE/AFTER command format, like this:

BEFORE path/to/filename.ext
```
... unchanged lines from the original file ...
... only include lines around needed changes! ...
... NEVER INCLUDE AN ENTIRE FILE! ...
```
AFTER
```
... new lines to replace them with ...
```

The ``` delimiters are very important!
'''
        return inp

    def run(self):
        inp = self.get_input()

        prompt = ''
        prompt += inp
        prompt += '\n###\n'
        prompt += 'Here is the content of the files. DO NOT OUTPUT CODE USING THIS FORMAT!!\n'
        prompt += self.get_files_message()

        messages = [
            dict(role = 'system', content = self.system_prompt),
            dict(role = 'user', content = prompt),
        ]
        file_msg_no = 1

        content = self.send(messages)

        while True:
            messages.append(
                dict(
                    role = 'assistant',
                    content = content,
                )
            )

            print()
            try:
                if self.update_files(content):
                    print()
            except Exception as err:
                print(err)
                print()

            inp = self.get_input()

            if False and self.files_modified():
                for fname in self.fnames:
                    self.add_file(fname)

                print('Files have changed, informing ChatGPT.')
                print()

                messages[file_msg_no] = dict(role = 'user', content = '<<outdated list of the files and their content -- removed>>')
                messages.append(
                    dict(
                        role = 'user',
                        content = self.change_notice + self.get_files_message(),
                    )
                )
                file_msg_no = len(messages)-1

            message = dict(role = 'user', content = inp)
            messages.append(message)
            content = self.send(messages)



    def send(self, messages):
        #dump(messages)

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

        resp = ''.join(resp)
        return resp


    pattern = re.compile(r'^(\S+)\n<<<<<<< ORIGINAL\n(.+?)\n=======\n(.+?)\n>>>>>>> UPDATED$', re.MULTILINE | re.DOTALL)

    def update_files(self, content):
        for match in self.pattern.finditer(content):
            path, original, updated = match.groups()
            self.do_before_after(path, original, updated)

    def do_before_after(self, fname, before, after):
        fname = Path(fname)
        content = fname.read_text().splitlines()
        before = [l.strip() for l in before.splitlines()]
        stripped_content = [l.strip() for l in content]
        where = find_index(stripped_content, before)

        if where < 0:
            raise ValueError(before)

        new_content = content[:where]
        new_content += after.splitlines()
        new_content += content[where+len(before):]
        new_content = '\n'.join(new_content) + '\n'

        fname.write_text(new_content)
        print('Applied CHANGE', fname)

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

Currently the speaker icons come before the text of each message. Move them so they come after the text instead.

Move the About and New Chat links into a hamburger menu.
'''
