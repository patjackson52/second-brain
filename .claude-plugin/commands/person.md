---
description: Create a new person entry with guided info gathering
argument-hint: <person name>
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# Create Person

Create a new person entry in the second-brain vault using adaptive info gathering.

## Instructions

1. Locate the vault using the resolve-vault skill
2. Use the gather-person skill to run an adaptive conversation with the user
3. The user provided this name/description: $ARGUMENTS
4. Pass the name to the gather-person skill as the person's name

If `$ARGUMENTS` is empty, ask for the person's name first.
