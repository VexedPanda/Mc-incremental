# Mc-incremental

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (`VexedPanda/Mc-incremental`). See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root, created lazily. See `docs/agents/domain.md`.

## Pull requests

This is a vibe-coded project: merge PRs yourself as soon as they're pushed, without waiting for review. Open them ready for review (not draft) and squash-merge them into `main`.

## Pack layout

The packwiz pack lives in `pack/` (only its contents ship to players; docs, CI and agent files stay at the root). Work on it from inside `pack/`: `packwiz modrinth add <slug>`, `packwiz url add <name> <url>` for GitHub-hosted jars (e.g. the GTCEu snapshot and `mc-incremental-prestige` releases), then `packwiz refresh`. CI fails if the index isn't refreshed, and exports a `.mrpack` artifact on every PR.
