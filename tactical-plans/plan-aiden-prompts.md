# Plan for Adding Aiden Prompts

I am a senior software engineer. You are an excellent software engineer who cares deeply about expressive, modern, elegant, idiomatic code. We often collaborate. Currently, we are enhancing an AI-based coding assistant named "aider". We began by adding a simple, non-invasive way to plug in an alternative set of prompts for the AI assistant, which we call a "prompt variant". Next, we will add prompts for a more elaborately defined and instructed expert AI persona named Aiden.

ALWAYS CARRY OUT THE FOLLOWING STEPS BEFORE CHANGING CODE!
- First, make sure I agree with the direction for the change.
- Then, update this plan to reflect our progress up to that point, and our plan for the changes.
- Make sure I agree with the plan and am ready for you to make the changes.

Note that my adding files to the chat doesn't necessarily mean I agree with a planned changes or am ready for you to start it.
Get my explicit agreement before making a set of code changes.

## Requirements for This Enhancement

Later, we plan to heavily customize the prompts for `EditBlockCoder`. Right now, we will just lay the groundwork for this by making the `gpt_prompts` used by `EditBlockCoder` configurable. 

Specific goals:
- We will propose this as a PR, but possibly it will live only in a fork.
- So, we need to make it minimally invasive to the code.
- Also, we want to follow existing configuration conventions very closely.
- Plus we want to be very respective of all other project standards and conventions.
- Although our only immediate goal is to customize the prompts for `EditBlockCoder` and `AskCoder`,
  we will do it in a way that can be naturally extended to the other `Coder` subclasses.
  We expect separate prompt subclasses must be configured for different `Coder` subclasses, because they likely use different prompts.

## Introduce a "prompt_variant" Configuration Option

We will introduce a new abstraction: a "variant" prompt class that provides an alternative set of
prompts for a `Coder` subclass. There will be a registry of such classes. `Coder` classes (initially
just `EditBlockCoder`) will check for the `prompt_variant` configuration option. If it is set,
they will look up their prompt class in the registry.

- (x) Add an argument "--prompt-variant" to `args.py`. Have it default to "default".
- (x) Create a class `EditBlockPromptsAiden` in `aider/coders/editblock_prompts_aiden.py`.
      Initially, this is a copy of `EditBlockPrompts`.
- (x) Create a list of prompt-variant classes `__all_prompt_variants__` in `aider/coders/coder_prompts.py`.

## Enhance `EditBlockCoder` to Support `prompt_variant`

- (x) Add code to `EditBlockCoder`'s `__init__`:
  - (x) If `prompt_variant` is "default", use the hardcoded `EditBlockPrompts()`.
  - (x) Otherwise, search `__all_prompt_variants__` for a class with matching class variables:
    - Its `edit_format` must match that of `EditBlockCoder`.
    - Its `prompt_variant` must match the configured `prompt_variant`.
  - (x) Add tests to `test_editblock.py` to verify that this initialization establishes the correct
    class for `EditBlockCoder.gpt_prompts`.

## Prepare to support `prompt_variant` for `AskCoder`

Make it possible for any `Coder` subclass to opt in to supporting prompt variants. 
Let them specify their default prompt class. Perhaps the subclass does both by explicitly initializing 
their superclasses with their default `gpt_prompts` class as an argument.

- ( ) Move the logic that finds `gpt_prompts` from `EditBlockCoder`'s `__init__` to `Coder`'s `__init__`.
- ( ) Create a class `AidenPrompts` in `aider/coders/aider_prompts.py`.
- ( ) Modify `EditBlockPromptsAiden` to delegate its prompt constants to `AidenPrompts`.
- ( ) Modify `AidenPrompts` to construct its prompts by assembling logical pieces,
  so we can use the same prompt constants to construct prompts for `AskPromptsAiden`,
  which will not have the ideas of modifying files nor of SEARCH/REPLACE blocks.
- ( ) Rename the prompts exported by `AidenPrompts` to reflect that they are specific to `EditBlockPromptsAiden`.
  (But each of those prompts should be mostly assembled from reusable internal prompt constants.)

## Support `prompt_variant` for `AskCoder`

- ( ) Create a class `AskPromptsAiden` in `aider/coders/ask_prompts_aiden.py`.
- ( ) Implement `AskPromptsAiden` to delegate its prompt constants to `AidenPrompts`,
  following the pattern used for `EditBlockPromptsAiden` and adding new exported prompt
  constants to `AidenPrompts` as needed.
