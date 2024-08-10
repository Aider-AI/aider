# Plan for Adding Aiden Prompts

I am a senior software engineer. You are an excellent software engineer who cares deeply about expressive, modern, elegant, idiomatic code. We often collaborate. Currently, we are enhancing an AI-based coding assistant named "aider". We have added a simple, non-invasive way to plug in an alternative set of prompts for the AI assistant, which we call a "prompt variant". Next, we will add prompts for a more elaborately defined and instructed expert AI persona named Aiden.

ALWAYS CARRY OUT THE FOLLOWING STEPS BEFORE CHANGING CODE!
- First, make sure I agree with the direction for the change.
- Then, update this plan to reflect our progress up to that point, and our plan for the changes.
- Make sure I agree with the plan and am ready for you to make the changes.

Note that my adding files to the chat doesn't necessarily mean I agree with a planned changes or am ready for you to start it.
Get my explicit agreement before making a set of code changes.

## Requirements for This Enhancement

We have laid the groundwork for customizing the prompts for `EditBlockCoder` by making the `gpt_prompts` used by `EditBlockCoder` configurable. Now, we will extend this to support `AskCoder` and create the Aiden persona prompts.

Specific goals:
- We will propose this as a PR, but possibly it will live only in a fork.
- We have made it minimally invasive to the code.
- We are following existing configuration conventions very closely.
- We are being very respectful of all other project standards and conventions.
- We have implemented the customization for `EditBlockCoder` and will now extend it to `AskCoder`.
- We will create separate prompt subclasses for different `Coder` subclasses, as they use different prompts.

## Completed Steps

### Introduce a "prompt_variant" Configuration Option

We have introduced a new abstraction: a "variant" prompt class that provides an alternative set of
prompts for a `Coder` subclass. There is a registry of such classes. `Coder` classes (currently
just `EditBlockCoder`) check for the `prompt_variant` configuration option. If it is set,
they look up their prompt class in the registry.

- (x) Added an argument "--prompt-variant" to `args.py`. It defaults to "default".
- (x) Created a class `EditBlockPromptsAiden` in `aider/coders/editblock_prompts_aiden.py`.
      Initially, this was a copy of `EditBlockPrompts`.
- (x) Created a list of prompt-variant classes `__all_prompt_variants__` in `aider/coders/coder_prompts.py`.

### Enhance `EditBlockCoder` to Support `prompt_variant`

- (x) Added code to `EditBlockCoder`'s `__init__`:
  - (x) If `prompt_variant` is "default", it uses the hardcoded `EditBlockPrompts()`.
  - (x) Otherwise, it searches `__all_prompt_variants__` for a class with matching class variables:
    - Its `edit_format` must match that of `EditBlockCoder`.
    - Its `prompt_variant` must match the configured `prompt_variant`.
  - (x) Added tests to `test_editblock.py` to verify that this initialization establishes the correct
    class for `EditBlockCoder.gpt_prompts`.

## Next Steps

### Prepare to support `prompt_variant` for `AskCoder`

Make it possible for any `Coder` subclass to opt in to supporting prompt variants. 
Let them specify their default prompt class. We will do this by moving the prompt variant selection logic to the `Coder` base class.

- (x) Move the logic that finds `gpt_prompts` from `EditBlockCoder`'s `__init__` to `Coder`'s `__init__`.
  - Add a `prompt_variant` parameter to `Coder.__init__`.
  - Create a `setup_prompt_variant` method in the `Coder` class.
  - Update `EditBlockCoder.__init__` to pass the `prompt_variant` to `Coder.__init__`.
- (x) Create `aider/coders/aiden_prompts.py`.
- (x) Refactor the Aiden persona prompt from `EditBlockPromptsAiden` to `aiden_prompts.py`.

### Support `prompt_variant` for `AskCoder`

- (x) Create a class `AskPromptsAiden` in `aider/coders/ask_prompts_aiden.py`.
- (x) Implement `AskPromptsAiden` to obtain the Aiden persona prompt from `aiden_prompts.py`.
- (x) Create an `AskCoder.__init__` that passes `prompt_variant` to `Coder.__init__`.
- (x) Add a test for `AskCoder` to verify that it uses the correct prompt class, as we did in `test_editblock.py`.

### Add Optional LangFuse Support

### Add Heuristics