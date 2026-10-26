# A Run takes place in one dimension, chosen at Prestige behind Dimension gates

Some resources only generate in the Nether or End (e.g. GregTech's tungsten and naquadah veins), so an overworld-only loop caps progression at about IV (see `docs/research/emc-economy.md`). We decided that each Run area lies wholly in one Run dimension, and that the players pick it at Prestige from Candidate areas. Nether and End become available only once the world's Knowledge passes their Dimension gate, which mirrors the progression a vanilla player needs to reach them (a portal for the Nether; eyes of ender, and therefore the Nether, for the End). This extends ADR-0001: still one world, but a Run area may lie in any of its dimensions.

## Considered Options

- **Linked areas per Run:** every Run has an area in each dimension, joined by portals. More content per Run, but the snapshot, sweep and border must span dimensions at once.
- **Prospecting (buying a sample of an unlearned resource with EMC):** reliable, but skips exploration. Rejected; reconsider per resource only if playtesting shows one is unreachable.
- **No other dimensions:** their resources only enter through trades, loot or Meta progression purchases. Simplest, but drops exploration as the way to discover them.

## Consequences

- The Prestige mod needs per-dimension placement and safe-spawn rules (Nether lava and ceiling, End void), and the border must confine the Run in whichever dimension it lies in.
- Choosing where to Prestige becomes the loop's central decision: each unlocked Run dimension offers exactly 3 Candidate areas, previewed with their vein types and structures.
- Structure-bound resources (blaze rods behind the End gate, wither skulls, shulker shells, echo shards) rarely fit in a 3×3 area, so Candidate areas are biased: while a resource that a Dimension gate needs is undiscovered, at least one candidate contains its source. Bias only shapes those 3 candidates and never adds more, however many resources are missing. At most one of a dimension's 3 candidates may offer nothing undiscovered, unless every resource that dimension can offer is already discovered. Re-rolling is supported but not advertised: Prestiging again, including with the console command while the selection screen is open, offers fresh candidates.
- Dimension gates: the Nether opens once Knowledge holds obsidian and flint and steel; the End once it holds an eye of ender, blaze powder and an ender pearl. Candidate-area bias only targets resources the world can already harvest (it holds a tool or machine of the ore's harvest level).
- End Run areas lie only on the outer islands and must hold enough land (as overworld candidates skip oceans); the dragon's island is excluded (whether it is ever reachable is the endgame question, #6).
- A Run stays in its dimension: portals do nothing during a Run, and the dimension only changes at Prestige.
- No dimension-specific starting items: a world past a gate has already learned the basics (logs, water) and buys them with EMC.
- Resources normally mined in other dimensions are priced in EMC by rarity, consistent with overworld ores, not by dimension.
