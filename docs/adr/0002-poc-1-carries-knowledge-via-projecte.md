# PoC 1 carries Knowledge over Prestige with ProjectE's EMC

For the first PoC, what survives a Prestige is Knowledge: the items (and later other resources) a player has learned, recreatable from EMC via ProjectE. We chose EMC over a separate skill tree or world-based recovery because it lets a player skip rebuilding production chains for anything already discovered, while still forcing a fresh start on blocks and tooling: as the Content mod's tooling gets more expensive, a starved Run area pushes the player to Prestige. ProjectE stores Knowledge on the player, so it survives ADR-0001's move to a new Run area.

## Considered Options

- **Keep only inventory:** too little carries over to feel like Meta progression.
- **Separate skill tree / meta mechanic:** still a candidate for later PoCs.
- **Fast recovery of world-based progress:** conflicts with leaving each Run area behind.

## Consequences

- ProjectE values items and fluids but cannot turn EMC back into fluids. A custom "EMC tank" is required.
- Mekanism chemicals, mana and other mod resources have no EMC support on 1.21.1; they need custom bridges or a Content mod that doesn't depend on them.
- Whether all Knowledge should carry over, or be unlocked gradually, is open (issue #4).
