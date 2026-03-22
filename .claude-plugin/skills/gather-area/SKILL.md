---
name: gather-area
description: Adaptive conversation to gather area-of-responsibility details and create an area entry. Use when the user invokes /sb:area.
tools: Read, Write, Bash, Glob, Grep
---

# Gather Area Info

Run an adaptive conversation to create a new area entry in the vault.

## Prerequisites

Use the resolve-vault skill first to locate the vault and load routes.yaml.

## Area Name Validation

The area name MUST match one of the allowed names from `routes.yaml` `areas.allowed`:
- Health, Family, Home, Finance, Work, Learning, Community

If the user's description doesn't match an existing area, ask:
"The closest existing area is '{closest}'. Should I use that, or would you like to add '{new-name}' to the allowed areas list?"

If adding a new area, append it to `_system/routes.yaml` under `areas.allowed`.

## Core Questions (always ask)

1. **Domain:** "What responsibility or life domain does this cover?"
2. **Healthy state:** "What does 'healthy' look like for this area? How do you know it's going well?"

Then ask: "Want to add more detail (recurring tasks, related people), or is this enough?"

## Extended Questions (if user wants more)

3. **Recurring:** "Any recurring tasks or regular reviews for this area?"
4. **People:** "Key people connected to this area?"

## Output

### File Location

`{vault}/2_areas/{AreaName}.md`

If the area needs sub-structure: `{vault}/2_areas/{AreaName}/overview.md`

### Frontmatter

```yaml
---
type: area
status: active
captured_at: {ISO-8601 timestamp}
source: claude-code
tags: [{derived}]
ai_generated: false
---
```

### Body Structure

```markdown
# {Area Name}

## What This Covers
{from question 1}

## Healthy State
{from question 2}

## Recurring Tasks
{if provided}

## Related People
{if mentioned — link to 5_people/ entries}
```

## Cross-Linking

Same as gather-project: detect people mentions, create stubs if needed.
