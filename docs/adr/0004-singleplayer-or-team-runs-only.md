# Everything is world-global: no owners, no per-player Runs

Nothing in the Pack has an owner. The Run, the Run area, EMC barrels, the EMC balance and Knowledge all belong to the world, and every player in it shares them, with no UI or configuration. A Prestige affects everyone in the world. We don't support independent players Prestiging separately on one server, because one player's Prestige must never disrupt another's Run, and per-player Run areas add a lot of complexity for an audience we don't have yet.

## Consequences

- ProjectE stores EMC and Knowledge per player, so the prestige mod keeps the world's EMC balance and Knowledge as the source of truth in world data and mirrors them into every player's ProjectE data (on join and on every change). EMC barrels therefore keep working with no players online, which ProjectE alone can't do.
- Anything one player learns or earns is shared with all players.
