---
name: gather-project
description: Adaptive conversation to gather project details and create a structured project entry. Use when the user invokes /sb:project.
tools: Read, Write, Bash, Glob, Grep
---

# Gather Project Info

Run an adaptive conversation to create a new project in the vault.

## Prerequisites

Use the resolve-vault skill first to locate the vault and load routes.yaml.

## Core Questions (always ask)

1. **Goal:** "What's the goal or outcome of this project? What does 'done' look like?"
2. **Next action:** "What's the first concrete next step?"

After these two, ask:

"Want me to capture more detail (people involved, timeline, dependencies), or is this enough to get started?"

## Extended Questions (if user wants more)

3. **People:** "Who's involved?" — Note names for cross-linking
4. **Timeline:** "Any deadline or target date?"
5. **Dependencies:** "Anything blocking this or that this depends on?"
6. **Related:** "Related areas or existing resources in the vault?"

The user can say "that's enough" at any point.

## Output

### File Location

Default: `{vault}/1_projects/active/{slug}.md`

If the user asks for more structure:
```
{vault}/1_projects/active/{slug}/
├── index.md        (main project file)
├── tasks.md        (task tracking)
└── decisions.md    (decision log)
```

### Frontmatter

```yaml
---
type: project
status: active
captured_at: {ISO-8601 timestamp}
source: claude-code
tags: [{derived from conversation}]
people: [{names mentioned}]
ai_generated: false
---
```

### Body Structure

```markdown
# {Project Title}

## Goal
{from question 1}

## Next Actions
- [ ] {from question 2}

## Context
{any additional detail from extended questions}

## People
{if mentioned — link to 5_people/ entries}

## Timeline
{if provided}
```

### Slug Generation

- Lowercase, hyphens, max 5 words
- Derived from the project title/goal
- Example: "buy-recteq-smoker", "kitchen-renovation"

## Cross-Linking

After creating the project file, check for people mentions:

1. For each person name mentioned:
   - Search `{vault}/5_people/` for existing file matching the name
   - If found: add a `## Related Projects` link in the person file
   - If not found: create a stub at `{vault}/5_people/work/{name-slug}.md`:

```yaml
---
type: person
stub: true
captured_at: {timestamp}
source: claude-code
ai_generated: false
---

# {Person Name}

_Stub created from project: {project-name}_
```

2. Add the person filename to the project's `people:` frontmatter list
