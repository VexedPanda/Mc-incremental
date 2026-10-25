# PoC 1: ProjectE + a tech Content mod

Status: being defined. Decisions here are cheap to change; hard-to-reverse ones live in `docs/adr/`.

## Settled

- **Carry-over:** ProjectE EMC (ADR-0002). A Prestige keeps the player's Knowledge **and** their EMC balance.
- **Wiped on Prestige:** the inventory, and the world as far as the player is concerned: they move to a fresh Run area and never return to the old one (ADR-0001).
- **Run area:** 3×3 chunks, kept as a tunable setting for play-testing.
- **Confinement:** the vanilla world border, re-centred on each new Run area.
- **Prestige trigger:** a craftable item, cheap enough to make from a single dirt, sand or cobblestone, that runs a KubeJS script: pick a far-away new area (re-pick if ocean), move the border, teleport, clear the inventory.
- **Prestige availability:** always available (no minimum achievement).

- **Content mod and version:** GregTech CEu Modern 8.0 snapshot (pinned) on 1.21.1 NeoForge, with ProjectE PE1.1.0 and KubeJS 2101 (ADR-0006).
- **Ore layout:** GT places one vein per layer on a 3-chunk grid, so each 3×3 Run area holds exactly one stone-layer and one deepslate-layer vein (e.g. iron ~1 in 7 Runs, diamond ~1 in 8.5). That per-Run lottery is the hook. The Prestige script centres each Run area on a GT grid point (chunk x and z both multiples of 3) so the veins sit inside the border. A thin baseline of scattered vanilla ores stays on (`removeVanillaOreGen=false`) so no Run soft-locks the steam age.
- **Allowed low-value inputs:** air, water, cobblestone (GT chemistry needs oxygen; plastics come from plant ethanol).
- **Removed free generation (ADR-0005):** GT Fluid Drilling Rig, Bedrock Ore Miner (`doBedrockOres=false`), the `stone_dust_separation` recipe (cobble to titanium/chrome trickle), ProjectE Energy Collectors and power flowers. Chunk loaders are banned.
- **Raw ore has 0 EMC** (ProjectE default): ore must be processed before it can be banked. Processed outputs have EMC, so this doesn't add grind.
- **Prestige sweep:** on Prestige, everything in the Run area that doesn't match the original worldgen (placed blocks, machines and the contents of every machine and storage inventory and tank, placed fluids, dropped items) is converted to EMC at **full value** and removed, so nothing valuable is left behind and nothing keeps generating EMC. Untouched natural blocks (unmined ore, terrain) are left alone and abandoned. The sweep diffs the area against a snapshot taken at Run start (ADR-0007).
- **Custom mod:** the Prestige controller (change tracking, sweep, new Run area, border, teleport, inventory wipe) and the EMC barrel (issue #10) live together in one repo, `mc-incremental-prestige` (ADR-0003); they can be split later.
- **EMC is lossless and reversible:** converting a resource to EMC and back nets zero (sell value equals EMC value).
- **Fluid EMC is explicit:** each fluid has its own EMC value per 1000 mB in the Pack's EMC data; it is never derived from buckets. Unmapped fluids are worth 0.
- **Power generation:** open question, issue #25.
- **EMC values for GT:** ProjectE ignores GT machine recipes, so GT parts and materials need a hand-made EMC value set.
- **Where EMC values live (#41):**
  - Item values: `pack/config/ProjectE/custom_emc.json` (ProjectE's own override file, `{"entries":[{"id":"<item>","emc":<long>}]}`). ProjectE applies it after its datapack defaults, so these values win. Entries may also be `{"tag":"c:ingots/iron","emc":64}`; the tags ProjectE gives default values (metal ingots, crops, wheat seeds) are pinned too, or recipes consuming the tag would price it at the default. The datapack route (`pe_custom_conversions`) lost to ProjectE's default tag values (e.g. `c:ingots/iron`), so it isn't used. First pass: GT metals with ingot = dust = plate, key parts (circuits, LV motor/pump/piston/conveyor/robot arm), casings and hulls, steam-age machines, metal blocks = 9 ingots; renewables low (iron 64, gold 128, crops 8, mob drops 4-32).
  - Fluid values: `pack/kubejs/data/mcincremental_prestige/fluid_emc/fluids.json` (datapack resource `mcincremental_prestige:fluid_emc/fluids.json`), read by the prestige mod. Format: `{"comment": "...", "emc_per_1000_mb": {"<fluid id>": <long>, ...}}`, keyed by source fluid id, value per 1000 mB. Unlisted fluids are worth 0. Water and steam are 0; lava and GT fuels are scarce. ProjectE can't hold fluid values at runtime, which is why this file exists.
  - Filled buckets are item values in `custom_emc.json` equal to the empty bucket plus the fluid's value, so bucketing a fluid neither gains nor loses EMC. The smoke test checks every listed fluid's bucket against the fluid file.
  - `covalenceLoss = 1.0` is pinned in `pack/config/ProjectE/server.toml`, so sell value equals EMC value.
  - ProjectE's fixed-ratio Philosopher's Stone conversions (4 gold to diamond, redstone to lava, ...) are removed (`pack/kubejs/server_scripts/emc_values.js`); with the Pack's values they would create EMC.

## Open

- **Resources missing from the Run area** (e.g. no diamonds): issue #12. Villager trades and EMC from earlier Runs are the current answers.
