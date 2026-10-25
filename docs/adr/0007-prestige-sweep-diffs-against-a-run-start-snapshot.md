# The Prestige sweep diffs the Run area against a snapshot taken at Run start

When a Run starts, the Prestige controller waits until the Run area's chunks are fully generated and ticking, then stores a compact copy of their block states. At Prestige, it compares the live chunks with that copy and sweeps whatever differs. We chose this because it catches every change regardless of cause (machines, pistons, fluids, explosions, other mods' direct writes), costs nothing during play, and has a fixed footprint: one snapshot of about 0.5–1.3 MB in memory and roughly 50–300 KB on disk, overwritten each Run, so nothing accumulates across Prestiges. A synthetic benchmark put the diff at about 0.1 ms typical and 5 ms worst case for 9 chunks.

## Considered Options

- **Track changes as they happen:** NeoForge's place/break events miss most changes (machines, pistons, fluid flow, growth, mods calling `setBlock`). A mixin on `LevelChunk.setBlockState` catches nearly everything but adds a cost to every block change in the game, and still needs the original states to diff.
- **Regenerate the original terrain from the seed and diff:** slow (hundreds of ms to seconds with modded worldgen), and fragile if worldgen isn't perfectly deterministic or a mod/config changes during a Run.

## Consequences

- Blocks whose Block is unchanged but whose properties changed (fence connections, crop age, leaf distance, redstone power) count as unchanged.
- Only changed positions with EMC value, a block entity, or a fluid source are swept, which filters out natural noise (mined-out holes, grass spread, leaf decay, flowing water).
- Unopened loot containers are skipped so the sweep can't roll loot into free EMC.
- Fluids, explosions and thrown items can reach past the world border, so the snapshot and sweep cover a one-chunk margin around the Run area (5×5 chunks).
- Implementation notes live in `mc-incremental-prestige/docs/prestige-sweep.md`.
