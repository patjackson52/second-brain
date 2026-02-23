---
name: resolve-vault
description: Discover the second-brain vault path and load routing configuration. Use whenever a command needs to read or write vault files.
tools: Read, Glob, Bash
user-invocable: false
---

# Resolve Vault

Locate the second-brain vault directory and load its routing configuration.

## Resolution Steps

1. Check `$VAULT_DIR` environment variable
2. If not set, default to `~/second-brain-vault`
3. Verify the directory exists and contains expected structure:
   - `0_inbox/` directory exists
   - `_system/` directory exists
   - `_system/routes.yaml` file exists
4. If vault not found, tell the user:
   - "Could not find second-brain vault. Set VAULT_DIR or run setup-vault.sh"
5. Read and parse `_system/routes.yaml`
6. Return vault path and routing config to the calling context

## What to Extract from routes.yaml

- `folders.*` — directory name mappings
- `areas.allowed` — list of valid area names
- `resources.allowed` — list of valid resource names
- `people.groups` — list of people subgroups (family, work, community, vendors)
- `uncertainty.keep_in_inbox_below_confidence` — confidence threshold (0.7)
- `hints.*` — keyword hints for classification
- `structure.projects.*` — project subfolder conventions
