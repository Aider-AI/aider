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

YOU MUST ONLY RETURN CODE USING THESE COMMANDS:
  - BEFORE/AFTER
  - DELETE
  - APPEND
  - PREPEND

** This is how to use the CHANGE command:

BEFORE path/to/filename.ext
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

DELETE path/to/filename.ext
```
... a series of sequential entire lines from ...
... the original file ...
... completely unchanged ...
... that will be deleted ...
```

** This is how to use the APPEND command:

APPEND path/to/filename.ext
```
... lines to add ...
... at the end of the file ...
```

** This is how to use the PREPEND command:

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

class Coder:
    fnames = []
    def system(self, prompt):
        self.system_prompt = prompt
    def file(self, fname):
        self.fnames.append(str(fname))
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
            self.update_files(content)
            inp = input()
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
        if cmd not in ('BEFORE', 'AFTER'):
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

    def do_before(self, cmd, fname, op_lines, after_op):
        after_cmd,after_fname,after_lines = self.parse_op(after_op)
        if after_cmd != 'AFTER':
            raise ValueError(after_cmd)
        if fname not in self.fnames:
            raise ValueError(fname)

        fname = Path(fname)

        content = fname.read_text()
        before = '\n'.join(op_lines)
        after = '\n'.join(after_lines)
        if before not in content:
            raise ValueError(before)

        content = content.replace(before, after)
        fname.write_text(content)





coder = Coder()
coder.file('../easy-chat/chat.css')
coder.update_files('''
BEFORE ../easy-chat/chat.css
```
.chat-box .fa-volume-up {
    color: #4CAF50;
}
```

AFTER
```
.chat-box .fa-volume-up {
    color: orange;
}
```
''')
sys.exit()

coder.system(prompt_webdev)

for fname in sys.argv[1:]:
    coder.file(Path(fname))

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
