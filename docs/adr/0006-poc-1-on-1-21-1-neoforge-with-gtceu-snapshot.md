# PoC 1 runs on 1.21.1 NeoForge with a pinned GTCEu 8.0 snapshot

PoC 1's Content mod is GregTech CEu Modern, on Minecraft 1.21.1 NeoForge, using a 1.21 8.0.0 snapshot pinned to one exact build. GT's stable line (7.5.3) is 1.20.1 Forge only, and ProjectE on 1.20.1 hasn't been updated since 2023. We accepted pre-release risk in a proof of concept to be on the newer version where both GT and ProjectE are actively developed.

## Considered Options

- **GTCEu 7.5.3 on 1.20.1 Forge:** stable, but an older platform with a stale ProjectE.
- **Modern Industrialization on 1.21.1:** stable and lighter, with vanilla-style scattered ores; it loses GT's per-Run ore lottery (see `docs/pocs/poc-1.md`).

## Consequences

- GT 8.0 changes the Java API and save format; scripts must target KubeJS 2101 and the 8.0 events.
- Updating the pinned snapshot is a deliberate step, tested before merging.
