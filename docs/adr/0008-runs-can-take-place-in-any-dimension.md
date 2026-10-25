# A Run takes place in one dimension, chosen at Prestige behind Dimension gates

Some resources only generate in the Nether or End (e.g. GregTech's tungsten and naquadah veins), so an overworld-only loop caps progression at about IV (see `docs/research/emc-economy.md`). We decided that each Run area lies wholly in one Run dimension, and that the players pick it at Prestige from Candidate areas. Nether and End become available only once the world's Knowledge passes their Dimension gate, which mirrors the progression a vanilla player needs to reach them (a portal for the Nether; eyes of ender, and therefore the Nether, for the End). This extends ADR-0001: still one world, but a Run area may lie in any of its dimensions.

## Considered Options

- **Linked areas per Run:** every Run has an area in each dimension, joined by portals. More content per Run, but the snapshot, sweep and border must span dimensions at once.
- **No other dimensions:** their resources only enter through trades, loot or Meta progression purchases. Simplest, but drops exploration as the way to discover them.

## Consequences

- The Prestige mod needs per-dimension placement and safe-spawn rules (Nether lava and ceiling, End void), and the border must confine the Run in whichever dimension it lies in.
- Choosing where to Prestige becomes the loop's central decision; Candidate areas show each area's dimension and vein types.
- Resources normally mined in other dimensions are priced in EMC by rarity, consistent with overworld ores, not by dimension.
