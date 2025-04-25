---
parent: Screen recordings
nav_order: 1
layout: minimal
highlight_image: /assets/recordings.jpg
description: Follow along as aider is modified to preserve read-only files specified at launch when using the /drop command. Aider does this implementation and adds test coverage.
---

# Don't /drop read-only files added at launch

<script>
const recording_id = "dont-drop-original-read-files";
const recording_url = "https://gist.githubusercontent.com/paul-gauthier/c2e7b2751925fb7bb47036cdd37ec40d/raw/08e62ab539e2b5d4b52c15c31d9a0d241377c17c/707583.cast";
</script>

{% include recording.md %}

## Commentary

- 0:01 We're going to update the /drop command to keep any read only files that were originally specified at launch.
- 0:10 We've added files that handle the main CLI and in-chat slash commands like /drop.
- 0:20 Let's explain the needed change to aider.
- 1:20 Ok, let's look at the code.
- 1:30 I'd prefer not to use "hasattr()", let's ask for improvements.
- 1:45 Let's try some manual testing.
- 2:10 Looks good. Let's check the existing test suite to ensure we didn't break anything.
- 2:19 Let's ask aider to add tests for this.
- 2:50 Tests look reasonable, we're done!







