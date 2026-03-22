---
description: Generate a daily summary of vault activity
argument-hint: [date in YYYY-MM-DD format]
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

## Vault Discovery

1. Check `$VAULT_DIR` environment variable for vault path
2. If not set, use `~/second-brain-vault`
3. Verify the vault exists by checking for `0_inbox/` directory

Generate a daily summary for the second-brain vault.

## Instructions

1. Get today's date by running: `date +%Y-%m-%d`

2. Check if `_system/summaries/daily/auto/daily-summary-<today>.md` already exists.
   - If it exists, inform the user and ask if they want to overwrite it.

3. Read through the vault to understand what changed today:
   - Check recently modified files across all directories
   - Review any notes created or updated today
   - Look at active projects for status

4. Generate a daily summary file at `_system/summaries/daily/auto/daily-summary-<today>.md` with this structure:

```
---
type: daily-summary
date: <YYYY-MM-DD>
generated_by: happy-automation
ai_generated: true
---

## What Changed Today

<List files created/modified today, summarize changes>

## Open Loops / TODO

<Pending items across projects, unresolved inbox items>

## Next Actions for Tomorrow

<Concrete next steps based on current state>

## Risks / Blockers

<Anything stalled or at risk>

## Questions for Patrick

<Clarifications needed, decisions to make>
```

5. Confirm to the user what was written.

$ARGUMENTS
