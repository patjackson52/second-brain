Generate a weekly summary for the second-brain vault.

## Instructions

1. Get the current ISO week by running: `date +%Y-W%V`

2. Check if `_system/summaries/weekly/auto/weekly-summary-<week>.md` already exists.
   - If it exists, inform the user and ask if they want to overwrite it.

3. Read through the vault to understand the week's activity:
   - Review daily summaries from this week in `_system/summaries/daily/auto/`
   - Check recently modified files across all directories
   - Look at project progress and status changes
   - Review new notes added this week

4. Generate a weekly summary file at `_system/summaries/weekly/auto/weekly-summary-<week>.md` with this structure:

```
---
type: weekly-summary
week: <YYYY-Www>
generated_by: happy-automation
ai_generated: true
---

## Highlights

<Key accomplishments and notable events this week>

## Progress by Theme

<Group updates by project or topic area>

## Open Loops / TODO

<Unresolved items carried forward>

## Next Actions

<Priority actions for the coming week>

## Questions for Patrick

<Decisions needed, clarifications, strategic questions>
```

5. Confirm to the user what was written.

$ARGUMENTS
