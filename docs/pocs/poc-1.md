# PoC 1: ProjectE + a tech Content mod

Status: being defined. Decisions here are cheap to change; hard-to-reverse ones live in `docs/adr/`.

## Settled

- **Carry-over:** ProjectE EMC (ADR-0002). A Prestige keeps the player's Knowledge **and** their EMC balance.
- **Wiped on Prestige:** the inventory, and the world as far as the player is concerned: they move to a fresh Run area and never return to the old one (ADR-0001).
- **Run area:** 3×3 chunks, kept as a tunable setting for play-testing.
- **Confinement:** the vanilla world border, re-centred on each new Run area.
- **Prestige trigger:** a craftable item, cheap enough to make from a single dirt, sand or cobblestone, that runs a KubeJS script: pick a far-away new area (re-pick if ocean), move the border, teleport, clear the inventory.
- **Prestige availability:** always available (no minimum achievement).

## Open

- **Content mod:** a GregTech-style tech mod (GTCEu / Monifactory-like) or similar, under evaluation.
- **Minecraft version/loader:** follows the Content mod; prefer the newest version the mods support.
- **Resources missing from the Run area** (e.g. no diamonds): issue #12.
