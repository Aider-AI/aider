---
parent: Screen recordings
nav_order: 1
layout: minimal
highlight_image: /assets/recordings.jpg
description: Watch the implementation of a warning system that alerts users when they try to apply reasoning settings to models that don't support them. Includes adding model metadata, confirmation dialogs, refactoring, and comprehensive test coverage.
---

# Warn when users apply unsupported reasoning settings

<script>
const recording_id = "model-accepts-settings";
const recording_url = "https://gist.githubusercontent.com/paul-gauthier/66b1b5aa7136147702c98afc4987c0d4/raw/4b5c7ddf7e80db1ff4dfa78fe158bc000fc42e0e/accepts-settings.cast";
</script>

{% include recording.md %}

## Commentary

- 0:01 Users sometimes run aider with "reasoning" settings that aren't supported by the model they're using. This can cause LLM API calls to completely fail, with non-specific error messages from the API provider. We're going to warn users up front to prevent this.
- 0:25 Ok, let's ask aider to add a new model setting where we can note which reasoning settings it supports. And then print a warning if the user tries to apply an unsupported setting.
- 1:30 Looks like it's including some extra changes we don't want.
- 1:45 Let's have a look at the models code and clean up some stray lines.
- 2:00 It also made the warning logic too conservative. We want to warn unless the setting is explicitly known to be supported.
- 3:00 Ok, good. Now lets add a setting to silence these warnings for power users who are doing something intentional.
- 3:45 Now we need to update the database of model settings to annotate which models support which reasoning settings. We'll start with the code that handles "fallback" settings for known models on unknown providers.
- 4:45 Oh, we forgot to give aider the actual file with that code! Aider asks to see it.
- 5:00 Ok, we've confused aider by asking it to change code it couldn't see.
- 5:10 Let's clear the chat and refine the prompt and try again.
- 6:00 Ok, looks good. Let's move on and update the full model settings database YAML file. Each main model like "o1" appears here from many providers, like OpenAI, OpenRouter, etc. We want to update them all.
- 7:43 Let's interrupt and refine the prompt to be more clear about which models to update.
- 9:20 Looks good. Let's review the YAML file and eyeball all the relevant models.
- 10:20 Now let's do some manual testing.
- 10:41 Ok, it should not be warning us about using "thinking tokens" with Sonnet 3.7.
- 10:55 Let's see if aider can spot the problem?
- 11:28 That doesn't sound like a promising solution. Let's add more of the relevant code, clear history and try again.
- 12:00 Ok, let's try aider's proposed solution.
- 12:32 And see if it worked... Nope! Still getting the unneeded warning. Undo that change!
- 12:48 Time for some manual print debugging.
- 13:00 It seems like the "accept_settings" value is not being set?
- 14:30 Aha! I have a local model settings file for Sonnet which overrides aider's built in settings. And we did not update it. Let's add "accepts_settings" there.
- 14:45 That was the problem, it wasn't a bug.
- 14:59 Ok, let's add test coverage for all this stuff.
- 15:09 And while aider writes tests, let's use "git diff" to review all the changes we've made.
- 15:34 Aider is done writing tests, let's try them.
- 15:44 One passed, one failed. Let's eyeball the passing test first.
- 16:04 And let's see if aider can fix the failing test.
- 16:14 Aider needs to see another file, which makes sense.
- 16:29 It's found the problem, but is trying to "fix" the code. We want it to fix the test.
- 16:47 Ok, tests are passing.
- 16:55 We should stop and ask the user "are you sure?", not just flash a warning if they're about to break their API calls.
- 17:59 Ok, that confirmation dialog looks good.
- 18:35 This code is a little bit repetitive. Let's do a bit of refactoring.
- 19:44 Sonnet is messing up the code editing instructions, so aider is retrying.
- 19:54 Let's clear the chat history and try again.
- 20:25 Are tests still passing after the refactor?
- 20:55 Tests passed, good. Let's tweak the warning text.
- 21:10 And now let's have aider update the docs to explain these changes.
- 22:32 Let's proofread and edit the updated docs.
- 24:25 And a "git diff" of all the docs changes to do a final check.
- 24:56 Let's have aider update the project's HISTORY file.
- 25:35 We can refine the HISTORY entries a bit.
- 26:20 All done!






