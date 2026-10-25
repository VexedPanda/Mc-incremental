# PoC 1: ProjectE + a tech Content mod

Status: being defined. Decisions here are cheap to change; hard-to-reverse ones live in `docs/adr/`.

## Settled

- **Carry-over:** ProjectE EMC (ADR-0002). A Prestige keeps the world's Knowledge **and** its EMC balance; both are world-global, shared by every player (ADR-0004).
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
- **ProjectE default EMC values (#47):** wherever ProjectE has a default value it applies (iron ingot 256, copper 128, gold 2048, diamond 8192, crops, mob drops, ...). Renewables are not devalued; they are judged by the exploit threshold instead: only a loop that lets a player create or duplicate roughly **100+ EMC in an automatable way** gets fixed, and each one is decided individually. Small free-EMC leaks are accepted. ProjectE's Philosopher's Stone conversions (4 gold to diamond, ...) and the Volcanite Amulet are kept: at default values they are EMC-neutral, and the amulet's lava (64 EMC per bucket, after 32 EMC of amulet fuel) is far below the threshold and can't be automated (ProjectE gives it no dispenser behaviour).
- **Where EMC values live (#41, re-based in #47):**
  - Item values: `pack/config/ProjectE/custom_emc.json` (ProjectE's own override file, `{"entries":[{"id":"<item>","emc":<long>}]}`). ProjectE applies it after its datapack defaults, so these values win; the datapack route (`pe_custom_conversions`) loses to ProjectE's default tag values (e.g. `c:ingots/iron`), so it isn't used. It holds only what ProjectE can't value: GT dusts, plates and blocks (dust = plate = ingot, block = 9 ingots), GT ingots with no ProjectE default (steel 512, wrought iron 256, zinc 512, brass 224, aluminium 1024, red alloy 384, derived from default iron/copper/redstone), key parts (circuits, LV motor/pump/piston/conveyor/robot arm), casings and hulls, steam-age machines, and GT fluid buckets. GT ingots ProjectE has a default for (tin 256, bronze 160, lead 512, silver 512, nickel 1024) get it through their `c:ingots/*` tag and are not pinned. No tags are pinned. The only vanilla entries are items GT's recipe changes leave at 0 EMC (its bucket and metal-block recipes need tools or machines ProjectE can't value): bucket 768, lava bucket 832, iron/gold/copper block = 9 ingots, i.e. ProjectE's own default values. It also pins the Transmutation Tablet at 0 (see below).
  - Fluid values: `pack/kubejs/data/mcincremental_prestige/fluid_emc/fluids.json` (datapack resource `mcincremental_prestige:fluid_emc/fluids.json`), read by the prestige mod. Format: `{"comment": "...", "emc_per_1000_mb": {"<fluid id>": <long>, ...}}`, keyed by source fluid id, value per 1000 mB. Unlisted fluids are worth 0. Water and steam are 0; lava is 64 (ProjectE's default lava bucket 832 minus empty bucket 768); GT fuels are hand-set. ProjectE can't hold fluid values at runtime, which is why this file exists.
  - Filled buckets equal the empty bucket plus the fluid's value, so bucketing a fluid neither gains nor loses EMC. The smoke test checks every listed fluid's bucket against the fluid file.
  - `covalenceLoss = 1.0` is pinned in `pack/config/ProjectE/server.toml`, so sell value equals EMC value.
  - Known small leaks (below the threshold, left as-is): crafting 9 GT tiny dusts into a dust gains 1 to 8 EMC (tiny dust value rounds down), as ProjectE's "EMC Exploit" log warnings list. `scripts/smoke-test.sh` accepts these and fails on any "EMC Exploit" warning that gains 100 EMC or more.
  - The Transmutation Tablet is pinned at **0 EMC** in `custom_emc.json`: the prestige mod gives it to players for free, so burning it or sweeping it on Prestige must yield nothing. The smoke test asserts it.
- **Emerald EMC is 64 (#53)**, down from ProjectE's 16,384, so villager trades can't mint EMC. Trading stays as a way to find resources.
  - Why 64 and not ~512 (wheat): a dump of every villager trade (all professions, levels 1–5, all 7 villager types) shows the cheapest trades that buy an emerald take items worth **0 EMC** in this Pack: 24 paper or 2 book and quills (librarian), 4 books (librarian), 9 glass bottles (cleric); the cartographer's 11 glass panes are also 0. GT's recipe changes leave paper, books, bottles and panes unvalued. A trade with 0-EMC inputs gains the emerald's whole value, so the emerald must stay **below 100** (the exploit threshold). The cheapest trades with valued inputs are 20 stone (20 EMC) and a boat (40 EMC), so at 64 every trade that buys an emerald gains 64 EMC at most. 64 is ProjectE's own value scale (a power of two, like redstone 64).
  - Pinned by the tag `c:gems/emerald` in `custom_emc.json` (the only pinned tag): ProjectE's default value sits on the tag, so pinning only `minecraft:emerald` leaves the tag at 16,384 and ProjectE reports an exploit.
  - The Philosopher's Stone conversions `emerald_to_diamond` (1 emerald → 2 diamonds) and `diamond_to_emerald` are removed (`pack/kubejs/server_scripts/emerald_emc.js`). #47 kept them because they were EMC-neutral at default values; at 64, emerald → 2 diamonds would turn 64 EMC into 16,384, and diamonds → emerald would throw 16,320 away. Transmutation still converts at the real values.
  - The smoke test asserts emerald EMC ≤ 99 and that both conversions are gone.
  - Emerald-derived items that ProjectE leaves at 0 (emerald block, GT emerald dust, plate and gems) stay at 0: they can't be bought from EMC, so they lose value but create none.
  - Other ways to get emeralds or to spend them on valuable items (enchanted diamond gear, golden carrots and glistering melons, bells, ...) were audited in #53 and put to the owner one at a time. They are not changed here.
- **Default view distances (#46):** for performance, the Pack's defaults cover the 3×3 Run area plus one surrounding chunk (radius 2, 5×5 chunks), matching the Prestige sweep margin. They are defaults only; players and server owners can raise them.
  - Client: `pack/options.txt` sets `renderDistance:2`, `simulationDistance:5` and `entityDistanceScaling:0.5` (the slider minimum); Minecraft fills in every other option.
  - Dedicated server: `pack/server.properties` sets `view-distance=2` and `simulation-distance=2`. Vanilla clamps view distance to 2..32, so 2 is its floor. Simulation distance has no server-side clamp (0 or even negatives are accepted), but entities only tick within that many chunks of a player, so 2 is the lowest value that keeps the whole Run area ticking when the player stands in a corner chunk.
  - Both files are marked `preserve = true` in `pack/index.toml` (set by hand; `packwiz refresh` keeps it), so packwiz-installer writes them on first install and never overwrites later changes. Both ship to clients and servers alike (index entries have no side); the unused one is harmless.
  - `scripts/smoke-test.sh` starts from the shipped `server.properties` and only overrides test keys (port, seed, online-mode, ...); the smoke test asserts the running server's view and simulation distance are 2.
  - **Singleplayer:** the integrated server copies the client's simulation distance option, whose slider can't go below 5. The Prestige mod lowers it every tick to `2 × radiusChunks` of the current Run area (2 for the default 3×3, matching the dedicated server); see the mod's `docs/simulation-distance.md` (#50). `options.txt`'s `simulationDistance:5` is just the slider minimum. Render distance stays the player's choice.

## Owner decisions (code review of #24)

The review flagged these as possible mismatches; the owner kept them as they are:

- **EMC values stay in two files:** items in `pack/config/ProjectE/custom_emc.json`, fluids in `pack/kubejs/data/mcincremental_prestige/fluid_emc/fluids.json`, because ProjectE can't hold fluid values.
- **Server `simulation-distance` stays 2:** the smallest value that keeps the whole 3×3 Run area ticking from a corner chunk. Singleplayer matches it via the Prestige mod's cap (#50); a larger configured Run area raises that cap automatically, but dedicated-server owners must raise `simulation-distance` themselves.
- **The vanilla pins stay:** `minecraft:bucket`, `minecraft:lava_bucket` and the iron/gold/copper blocks are pinned in `custom_emc.json`. They equal ProjectE's defaults; GT's recipes would otherwise leave them at 0.

## Open

- **Resources missing from the Run area** (e.g. no diamonds): issue #12. Villager trades and EMC from earlier Runs are the current answers.
