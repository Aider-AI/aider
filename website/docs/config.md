---
nav_order: 55
has_children: true
description: Information on all of aider's settings and how to use them.
---

# Configuration

Aider has many options which can be set with
command line switches.
Most options can also be set in an `.aider.conf.yml` file
which can be placed in your home directory or at the root of
your git repo. 
Or via environment variables like `AIDER_xxx`,
as noted in the [options reference](options.html).

Here are 3 equivalent ways of setting an option. First, via a command line switch:

```
$ aider --dark-mode
```

Or, via an env variable:

```
export AIDER_DARK_MODE=true
```

Or in the `.aider.conf.yml` file:

```yaml
dark-mode: true
```

