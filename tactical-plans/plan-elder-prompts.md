# Plan for Adding Elder Prompts

I am a senior software engineer. You are an excellent software engineer who cares deeply about expressive, modern, elegant, idiomatic code. We often collaborate. Currently, we are enhancing an AI-based coding assistant named "aider". 

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
- Although our only immediate goal is to customize the prompts for `EditBlockCoder`,
  we will do it in a way that can be naturally extended to the other `Coder` subclasses.
  We expect separate prompt subclasses must be configured for different `Coder` subclasses, because they likely use different prompts.
- In the future, we plan to propose how the aider project could support a community-contributed library of prompts.
  Although we won't propose that now, nor take explicit steps toward it, we'd like our current changes to lead there naturally.

## Designing Our Prompt Configuration

### Study the Project's Existing Configuration Conventions

- ( ) Figure out which project files to examine to understand this, and ask me to add them to the chat.
- ( ) Examine existing project files to understand how other configuration options work, both in config files and in the code.
- ( ) Take notes in this document on what we discover that is most applicable to this current enhancement.

### Design Our Approach

- ( ) Write down our planned approach in ths document.
- ( ) Extend this plan to a full implementation of our approach.
