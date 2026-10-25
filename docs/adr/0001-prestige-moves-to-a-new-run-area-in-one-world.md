# Prestige moves the player to a new Run area in one ordinarily generated world

A Prestige does not create a new save, a new dimension or a new seed. The whole game happens in one ordinarily generated world, and a Prestige moves the player (or team) to a fresh, never-visited Run area far from earlier ones. Variety comes from the world being large and varied, not from regenerating it. We chose this because player data (inventory, ProjectE Knowledge, quest progress) carries over for free inside one save, and because nothing on 1.21.1 gives runtime dimensions their own seed without reflection hacks or custom code.

## Considered Options

- **New save folder per Run:** loses all player data unless exported and re-imported by script.
- **New runtime dimension per Run (e.g. Infiniverse):** a fresh seed per dimension is only built in from Minecraft 26.1 (`copy_dimension … random_seed`); on 1.21.1 every new dimension shares the overworld seed.
- **Chunk By Chunk style (copy chunks in from a hidden generation dimension):** good design, but the mod stopped at 1.20.4 and its 1.21.1 fork (Gathering Chunks) is a beta with no source found.

## Consequences

- Old Run areas stay on disk; save size grows with every Prestige. Pruning old regions may be needed later.
- Something must keep the player inside the current Run area (e.g. a world border re-centred on each Prestige).
