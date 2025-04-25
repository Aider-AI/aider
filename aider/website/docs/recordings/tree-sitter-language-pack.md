---
parent: Screen recordings
nav_order: 0
layout: minimal
highlight_image: /assets/recordings.jpg
description: Watch how aider adds support for tons of new programming languages by integrating with tree-sitter-language-pack. Demonstrates using aider to script downloading a collection of files, and using ad-hoc bash scripts to have aider modify a collection of files.
---

# Add language support via tree-sitter-language-pack

<script>
const recording_id = "tree-sitter-language-pack";
const recording_url = "https://gist.githubusercontent.com/paul-gauthier/a990333449b09e2793088a45eb1587f4/raw/364124781cca282907ccdc7567cdfc588a9b438b/tmp.redacted.cast";
</script>

{% include recording.md %}


## Commentary

- 0:01 We're going to add a ton of new languages to aider via tree-sitter-language-pack.
- 0:10 First, lets try and find which languages it supports.
- 1:00 Ok, there's a language definitions json file
- 1:10 Does it have the github repos for each language?
- 1:29 Ok, this is what we need.
- 1:45 We need to get all the tags files from each repository for aider's repo-map. Let's have aider write a script to fetch them all.
- 2:05 We'll show aider the language definitions json file.
- 3:37 Looks like it can't find most of the tags.scm files.
- 4:19 Maybe we should have it try other branches besides master?
- 5:02 Ok, it seems to be downloading them now.
- 5:55 Let's make it so we can re-run the script and only download files we haven't fetched yet.
- 6:12 I see lots of tags files, so it's working.
- 6:30 Ok, restart to run with latest code. This will take awhile to fetch them all.
- 9:02 The Grep-AST module needs to know about all the new languages.
- 9:45 Let's have aider add them all, and register each using their commonly used file extensions.
- 10:15 Some of the languages need to be recognized by their base name, not by their extension.
- 11:15 Let's sanity check if Grep-AST can handle PowerShell, one of the new languages.
- 12:00 Looks like it's parsing PowerShell fine.
- 13:00 Ok, let's download all the tags files into the right spot in the aider repo.
- 14:00 This will take a minute...
- 16:07 Delete some no-op or empty tags files.
- 16:16 Let's commit all the unmodified tags files.
- 16:33 We need to update each tag file, so that aider can identify names of functions, classes, etc in all these languages.
- 17:01 Let's use a bash loop to script aider to modify each tags file.
- 17:12 I'm giving aider a read-only example of an already modified tags file, as an example to follow.
- 19:04 Looks like it correctly updated the first couple of tags files.
- 19:28 Let's grep to watch aider's progress working through the list of files.
- 20:20 It's working on the Dart language now...
- 20:50 E-lisp is up next...
- 21:30 This is going to take a little while...
- 24:39 Let's add a README file with attribution for these tags files.
- 26:55 Ok, all the files are updated with tags for definitions and references to named code objects.
- 27:10 Let's add test coverage to be sure these languages work with the repo-map.
- 27:19 Each language needs a "fixture" with some sample code to parse during the test. Let's show aider the layout of the fixtures directory.
- 27:50 We can use a bash loop to ask aider to add test coverage for each new tags file.
- 28:12 We'll pass the fixtures directory listing to aider.
- 28:52 Just need to fix the bash to correctly iterate through the list of tags files.
- 29:27 I forgot to ask aider to actually generate a sample code fixture for each language.
- 30:25 Lets run the repo-map tests to see if the first new test works.
- 30:37 Tests for the Arduino language failed, with an empty repo-map? That's not good.
- 31:52 Can aider figure out what's wrong?
- 32:27 Well, aider made the test pass by basically skipping Arduino.
- 32:36 Let me see if I can use Grep-AST on the new Arduino fixture code.
- 32:42 Oh! I'm not using the updated Grep-AST that knows about all the new languages.
- 32:54 Ok, now we're parsing Arduino code properly. Undo aider's bogus test fix.
- 33:05 Ok, arduino passes now but there seems to be a regression with tsx?
- 33:20 Can aider figure out why?
- 34:10 Let's check the parsers map.
- 35:00 Well, that's all for this recording. The tsx problem was due to a bad mapping from ".tsx" to "typescript" in the map that aider generated earlier.











