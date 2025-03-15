---
parent: Screen recordings
nav_order: 0
layout: minimal
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
- 1:45 We need all the tags files from each language's repository. Let's have aider write a script to fetch them all.
- 2:05 Let aider read the language definitions json file.
- 3:37 Looks like it can't find most of the tags.scm files.
- 4:19 Have it try other branches besides master.
- 5:02 Ok, it's downloading them now.
- 5:55 Let's make it so we can re-run and avoid re-downloading.
- 6:12 I see lots of tags files.
- 6:30 Ok, restart to run with latest code. This will take awhile to fetch them all.
- 9:02 The grep-ast module needs to know about all the new languages.
- 9:45 Let's have aider add them all, including their file extensions.
- 10:15 Some of the languages need to be recognized by their base name, not extension.
- 11:15 Let's sanity check if grep-ast can handle PowerShell now.
- 12:00 Looks like it's parsing PowerShell fine.
- 13:00 Ok, let's download the tags into the right spot in the aider repo.
- 14:00 This will take a minute...
- 16:07 Delete some bad or empty tags files.
- 16:16 Add the tags to the repo.
- 16:33 The tags files need to be modified to work with the repo-map.
- 17:01 Let's use bash to script aider to modify each tags file.
- 17:12 I'm giving aider a read-only example of working tags file, as an example to follow.
- 19:04 Looks like it correctly updated the first couple of tags files.
- 19:28 Let's grep to watch how many name tags are left to be updated.
- 21:30 This is going to take a little while...
- 24:39 Let's add a README file with attribution for these tags files.
- 27:00 Ok, all the tags files are updated.
- 27:10 Let's add test coverage to be sure these languages work with the repo-map.
- 27:19 Dump the fixtures directory structure to a file, to give aider so it knows the layout.
- 27:50 Use a bash script to ask aider to add test coverage for each tags file.
- 28:12 Let aider read the fixtures directory listing.
- 28:52 Just fixing the bash to correctly iterate through the list of tags files.
- 29:27 Improve the prompt to make sure aider creates a fixture for each language.
- 30:25 Lets run the repo-map tests to see if the new test works.
- 30:37 Arduino failed, with an empty repo-map?
- 31:52 Can aider figure out what's wrong?
- 32:42 Oh! I'm not using the updated grep-ast yet.
- 32:54 Ok, now we're parsing Arduino code properly. Undo that bogus test fix.
- 33:05 A regression with tsx?
- 33:20 Can aider figure out why?
- 34:10 Let's check the parsers map.
- 35:10 Well, that's all for this recording.











