---
description: Create a new area-of-responsibility entry with guided info gathering
argument-hint: <area name or description>
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# Create Area

Create a new area entry in the second-brain vault using adaptive info gathering.

## Instructions

1. Locate the vault using the resolve-vault skill
2. Use the gather-area skill to run an adaptive conversation with the user
3. The user provided this initial description: $ARGUMENTS
4. Pass the description to the gather-area skill as starting context — validate against routes.yaml allowed areas

If `$ARGUMENTS` is empty, start the conversation from scratch.
