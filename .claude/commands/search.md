Full-text search across the entire second-brain knowledge base.

## Instructions

Search for: `$ARGUMENTS`

1. Search across ALL directories: `0_inbox/`, `1_projects/`, `2_areas/`, `3_resources/`, `4_archive/`, `5_people/`, `_system/summaries/`
2. Search within:
   - File contents (body text)
   - Filenames
   - YAML frontmatter (tags, type, status, etc.)
3. Return results with:
   - File path
   - Relevant context snippet (a few lines around the match)
   - Frontmatter metadata summary (type, tags if present)
4. Order results by relevance
5. If no results found, say so clearly

$ARGUMENTS
