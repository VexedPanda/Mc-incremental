# One team per world owns the Run; no per-player Runs

Every player in a world automatically belongs to the same single **Team**, with no UI or configuration. The Team, not any player, owns the Run, the Run area, EMC barrels, the EMC balance and Knowledge. A Prestige affects everyone in the world. We don't support independent players Prestiging separately on one server, because one player's Prestige must never disrupt another's Run, and per-player Run areas add a lot of complexity for an audience we don't have yet.

## Consequences

- ProjectE stores EMC and Knowledge per player, so the prestige mod keeps the Team's EMC balance and Knowledge as the source of truth in world data and mirrors them into every player's ProjectE data (on join and on every change). This also means EMC barrels keep working while players are offline, which ProjectE alone can't do.
- Anything one player learns or earns is shared with all players.
