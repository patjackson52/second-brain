---
name: gather-person
description: Adaptive conversation to gather person details and create a people entry. Use when the user invokes /sb:person.
tools: Read, Write, Bash, Glob, Grep
---

# Gather Person Info

Run an adaptive conversation to create a new person entry in the vault.

## Prerequisites

Use the resolve-vault skill first to locate the vault and load routes.yaml.

## Core Questions (always ask)

1. **Relationship:** "How do you know {name}?" — Determines subgroup:
   - Family → `5_people/family/`
   - Colleague/work → `5_people/work/`
   - Friend/neighbor/community → `5_people/community/`
   - Service provider/business → `5_people/vendors/`
2. **Context:** "What's the key context to remember about {name}?"

Then ask: "Want to add more (contact info, related projects, follow-ups), or is this enough?"

## Extended Questions (if user wants more)

3. **Contact:** "Any contact info to store? (email, phone, etc.)"
4. **Related:** "Any active projects or areas connected to {name}?"
5. **Follow-ups:** "Any pending follow-up items with {name}?"

## Output

### File Location

`{vault}/5_people/{subgroup}/{name-slug}.md`

### Frontmatter

```yaml
---
type: person
relationship: {family|work|community|vendor}
captured_at: {ISO-8601 timestamp}
source: claude-code
tags: [{derived}]
ai_generated: false
---
```

### Body Structure

```markdown
# {Person Name}

## Context
{from question 2}

## Contact
{if provided}

## Related Projects
{if mentioned — link to 1_projects/ entries}

## Related Areas
{if mentioned — link to 2_areas/ entries}

## Follow-ups
{if provided}
- [ ] {follow-up items}
```

## Cross-Linking

If the user mentions projects or areas:
1. Search vault for matching project/area files
2. If found: add backlink to the person in the project/area file's `## People` section
