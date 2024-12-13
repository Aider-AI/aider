# Mixture of Architects (MOA)

## Overview

The Mixture of Architects (MOA) is a collaborative AI architecture where multiple LLM "architects" work together to solve programming tasks. Each architect maintains its own conversation thread while being able to see and respond to other architects' proposals.

## Core Concepts

### Architects
- Multiple architects (LLMs) participate in the discussion
- Each architect is identified by a NATO phonetic name (alpha, bravo, charlie, etc.)
- The first architect (alpha) is always the main model
- Each architect sees all other architects' proposals, enabling true collaborative discussion

### Discussion Flow

The discussion proceeds in rounds, with each round following this pattern:

1. User submits a query/request
2. Architects respond sequentially:
   - Each architect sees:
     - Original user query
     - All previous architects' proposals (XML fenced)
   - Each architect provides:
     - Their analysis/instructions
     - Their own proposal (in XML fence)
   - Can reference, support, critique or object to other architects' proposals

For example, in a 3-architect system:

#### Alpha's View
```
User Query 1
└── Alpha Response + Proposal
    └── Bravo's Proposal
        └── Charlie's Proposal
            └── User Query 2
                └── Alpha Response + Proposal
                    └── Bravo's Proposal
                        └── Charlie's Proposal
```

#### Bravo's View
```
User Query 1 + Alpha's Proposal
└── Bravo Response + Proposal
    └── Charlie's Proposal
        └── User Query 2 + Alpha's Proposal
            └── Bravo Response + Proposal
                └── Charlie's Proposal
```

#### Charlie's View
```
User Query 1 + Alpha's Proposal + Bravo's Proposal
└── Charlie Response + Proposal
    └── User Query 2 + Alpha's Proposal + Bravo's Proposal
        └── Charlie Response + Proposal
```

### Commands

Users can interact with MOA using three main commands:

1. `/discuss <message>` (or just type normally) - Start/continue a discussion round
2. `/code <message>` - Move to implementation phase
3. `/drop <architect-name>` - Remove an architect from the discussion

### Implementation Phase

When moving to implementation (`/code`), the entire discussion history is compiled chronologically with full context:

```
User Query 1
└── Alpha Full Response (analysis + proposal)
    └── Bravo Full Response (analysis + proposal)
        └── Charlie Full Response (analysis + proposal)
            └── User Query 2
                └── Alpha Full Response (analysis + proposal)
                    └── Bravo Full Response (analysis + proposal)
                        └── Charlie Full Response (analysis + proposal)
```

The complete history, including all analyses and proposals, is passed to the editor coder. The editor coder then decides how to implement the changes based on:
- The full discussion history
- The final user message
- Their own analysis of the proposals

## XML Fencing

The system uses XML fencing to maintain clear boundaries:

- `<user_message>` - Contains user queries
- `<proposal>` - Contains an architect's specific proposal
- `<architect name='NAME'>` - Contains full architect responses

## Collaborative Design

Key aspects of MOA:
- All architects see all proposals
- Architects can directly reference and critique each others' proposals
- No formal consensus mechanism - the editor coder makes implementation decisions
- The user guides the final implementation through their `/code` message
