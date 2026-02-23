---
description: Create a new project with guided info gathering
argument-hint: <brief project description>
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# Create Project

Create a new project entry in the second-brain vault using adaptive info gathering.

## Instructions

1. Locate the vault using the resolve-vault skill
2. Use the gather-project skill to run an adaptive conversation with the user
3. The user provided this initial description: $ARGUMENTS
4. Pass the description to the gather-project skill as starting context — use it to pre-fill what you can and skip questions already answered by the description

If `$ARGUMENTS` is empty, start the conversation from scratch.
