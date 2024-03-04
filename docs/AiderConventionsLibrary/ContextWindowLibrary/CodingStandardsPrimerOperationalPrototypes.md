Design Principles and Preferences for Operational Prototypes
===========================================================

This document outlines a realistic approach to design principles and preferences for creating Proof Of Principle implementations by small research teams. It aims to balance the need for structure with the agility required in research settings.

Simplified Automated Testing
----------------------------
While comprehensive testing may be ideal, small teams may lack the resources. Focus on the most critical tests that provide the highest value:

- **Essential Unit Tests**: Write tests for core functionality to catch major issues.
- **Basic Integration Tests**: Ensure key components interact correctly.
- **Manual End-to-End Testing**: Conduct manual tests for complex user interactions when automated end-to-end testing is not feasible.

Streamlined Version Control Practices
-------------------------------------
Version control is essential, but the process should be simplified:

- **Main and Development Branches**: Use a main branch for stable code and a development branch for ongoing work.
- **Simple Commit Strategy**: Commit often with clear messages that summarize the changes without elaborate structures.
- **Basic Pull Requests**: For teams of 2-3, informal code reviews can be conducted before merging changes from the development to the main branch.

Targeted Documentation
----------------------
Documentation is necessary, but it should not be overwhelming:

- **Code Comments**: Comment on complex algorithms and decisions that are not immediately obvious from the code.
- **README Files**: Maintain a README file with setup instructions, basic usage examples, and a brief overview of the project structure.
- **In-Code API Documentation**: Document public interfaces directly in the code to assist with onboarding and future reference.

By focusing on these key areas, small research teams can create operational prototypes that are robust enough for alpha testing while remaining agile and responsive to the research process.

Use of SparsePrimingRepresentation (SPR):
------------------------------------------
- We adopt SPR as a standard practice for efficient communication within the project.
- SPR terms are concise, descriptive, and written in PascalCase, encapsulating complex concepts for ease of discussion.
- SPR terms should be used consistently across all project documentation and communication channels.

Instructions for Suggesting New SPR Terms:
------------------------------------------
- Always be on the lookout for opportunities to improve communication efficiency through new SPR terms.
- When a potential new SPR term is identified, document the term, its intended meaning, and examples of its use.
- Suggest the new SPR term for approval before adding it to the project lexicon.
- Upon approval, add the new SPR term to the `SparsePrimingRepresentation.yaml` file with its definition and examples.

This approach to creating operational prototypes ensures that our project evolves efficiently, with a shared understanding that enhances collaboration and innovation.

# Copyright
 Copyright (c) 2023 Bjorn Heijligers, Chairman of Stichting "De Stichting" / TheFoundation.global
 Origin for the importance of SPRs when working with LLMs:
 David Shapiro - https://github.com/daveshap/SparsePrimingRepresentations
 # License
 MIT License
