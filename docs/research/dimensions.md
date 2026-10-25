# Nether, End and out-of-area materials: facts for the design discussion

Legend: **[V]** read in source/data or measured on the pack (GTCEu 8.0 snapshot 8602baa, NeoForge 21.1.264, pack config
from `integration/poc1-pack`). **[V-model]** output of the recipe-reachability model below (rigorous over the dumped
recipes, approximate on machine rules). **[E]** estimate.

Method, in short:
- Vanilla/NeoForge source: `neoforge-21.1.264-sources.jar` (from the mod's moddev build), vanilla data from the
  `client-extra` resources jar.
- GT worldgen: the `ore_vein/*.json` and `bedrock_fluid/*.json` inside the pack's GTCEu jar.
- One boot of a copy of the econ server (a copy of the smoke-test server, fresh world `dims-seed-1`, script
  `kubejs/server_scripts/zz_dims.js`): dumped all 34,845 recipes + item/fluid tags, checked the border in every
  dimension, scanned structures for 250 Run-like 3x3 areas (random grid centres within ±2,000 chunks, oceans
  included), 40 Nether windows (48x48 at the scaled centre, every block counted) and 30 End windows (+250 for
  structures). Raw logs not committed.
- Reachability model (`dimensions/*.py`): fixed-point closure over every recipe. Seeds = blocks seen in the
  research's 124 overworld areas + common drops + overworld mob drops (incl. ender pearl, witch glowstone) + wandering-
  trader goods; per scenario add Nether/End veins, blocks and mob drops. A GT recipe fires only if a machine that can
  run it is itself reachable (single-block of tier >= recipe tier; steam machines up to LV, from
  `SimpleSteamMachine.recipeModifier`; multiblock controller + energy hatch of tier >= recipe tier - 1; EBF coil temp +
  100 K/tier above MV; fusion MK by `eu_to_start`; cleanroom; research data item). Chanced byproducts count as
  available (quantity ignored). Pack removals honoured: fluid drilling rigs, bedrock ore miner, stone-dust centrifuge.
  Sanity check: with everything seeded it reaches complete UV and all three fusion reactors.

## 1. World border, portals, and the Prestige mod

### Border [V source + V measured]
- `MinecraftServer.createLevels` (sources l.423): every non-overworld level gets
  `overworldBorder.addListener(new DelegateBorderChangeListener(level.getWorldBorder()))`, then the overworld border
  `applySettings`. One shared border state, pushed to each dimension.
- `DelegateBorderChangeListener` forwards `setSize`, `lerpSizeBetween`, `setCenter`, warning and damage settings
  verbatim.
- `Level` constructor: if `dimensionType.coordinateScale() != 1.0`, the level's `WorldBorder` overrides only
  `getCenterX/Z()` to return `centre / coordinateScale`. **Size is never scaled.**
- `dimension_type/the_nether.json`: `coordinate_scale: 8.0`; overworld and End 1.0.
- Measured with the overworld border set to 48 wide at (32008, 24008):

| Dimension | Centre | Size | Bounds |
|---|---|---|---|
| Overworld | 32008, 24008 | 48 | x 31984..32032 |
| Nether | **4001, 3001** (= /8) | **48** | x 3977..4025 |
| End | 32008, 24008 | 48 | x 31984..32032 |

So for a Run area centred at (x, z): the **Nether area is 48x48 blocks at (x/8, z/8)** (it covers the equivalent of
384x384 overworld blocks, and is **not** aligned to chunks or GT's 3-chunk vein grid); the **End area is the same
3x3 chunks** as the Run. The research doc's "1/8 size, ~6x6 blocks" guess is wrong.
- Successive Run areas are >= 64 chunks apart, so their Nether areas are >= 128 blocks apart: they never overlap [V
  arithmetic].
- Border damage (`LivingEntity.baseTick` l.417, defaults `damagePerBlock 0.2`, `safeZone 5`): damage per tick-check =
  `floor((distance outside - 5) * 0.2)`. The mod only calls `setCenter`/`setSize`, so the defaults apply [V].

### Nether portal [V source]
`NetherPortalBlock.getPortalDestination`: destination = `netherBorder.clampToBounds(x * 1/8, y, z * 1/8)`, then
`PortalForcer.findClosestPortalPosition(..., worldBorder)` or `createPortal`, which only places inside the border.
A portal anywhere in the Run area maps to within ~4 blocks of the Nether area's centre, so **portals work both ways**
and always land inside the borders. Obsidian is available in-area (lava in 91% of areas [V research dump]; ruined
portals also carry obsidian/flint-and-steel).

### End [V source + E]
- `EndPortalBlock.getPortalDestination` sends the player to the hard-coded `END_SPAWN_POINT (100, 50, 0)` with **no
  border clamp**. With the End border at the Run area (>= ~1,000 blocks from the origin, usually tens of thousands),
  the player arrives far outside the border and takes `floor((d - 5) * 0.2)` damage per check, i.e. hundreds or
  thousands per hit: **certain death** [V code, E outcome].
- Reaching an End portal also needs a stronghold portal room inside the 3x3 area. Strongholds: 128 in concentric
  rings, first ring 3 at ~1,280-2,816 blocks. In 250 sampled areas: 0 strongholds [V]. P(portal room in a given
  area) ~ 3 x 2,304 / 19.8M ≈ 0.04% in ring 1, less further out [E]. No recipe makes `end_portal_frame` [V recipe
  dump]. End gateways need the dragon (origin island).
- **So the End is effectively unreachable.** But the End area at the Run's coordinates usually has terrain:
  end stone in 26/30 measured windows (mean 30,700 blocks), chorus in 9/30, end city pieces in 4/250 areas [V].

### Prestige mod (`integration/poc1-mod`) [V source]
- `RunAreas.beginRun` sets only the overworld border (`setCenter`, `setSize`); the delegates move the Nether/End
  borders automatically.
- `RunAreas.teleport` calls `player.teleportTo(server.overworld(), ...)` and resets the respawn point to
  `Level.OVERWORLD`, so a player in the Nether/End at Prestige is pulled back. `MissedPrestige` defers the teleport
  one tick for players logging in outside the overworld.
- `RunSnapshots` and `PrestigeSweep` read `server.overworld()` only. **Nothing in the Nether or End is snapshotted,
  swept or refunded**; machines or chests left in a Nether area are stranded outside the next border (not destroyed,
  not refunded). No code mentions `NETHER`/`END` or portals.

## 2. GTCEu 8.0 ore generation by dimension

### Vein definitions [V `ore_vein/*.json`]
Weight share is within the layer. `oreVeinGridSize: 3`, `oreVeinRandomOffset: 12` (pack config).

**Nether** (layer `netherrack`, total weight 575):

| Vein | Weight | Share | Y | Materials (weight) |
|---|---:|---:|---|---|
| sulfur | 100 | 17.4% | 10-30 | sulfur 3, pyrite 2, **sphalerite 1** |
| nether_quartz | 80 | 13.9% | 40-80 | nether quartz 3, quartzite 1 |
| tetrahedrite | 70 | 12.2% | 80-120 | tetrahedrite 4, copper 2, stibnite 1 |
| topaz | 70 | 12.2% | 80-120 | blue topaz 3, topaz 2, chalcocite 2, bornite 1 |
| nether_redstone | 60 | 10.4% | 5-40 | redstone 3, ruby 2, cinnabar 1 |
| certus_quartz | 40 | 7.0% | 80-120 | quartzite 3, certus quartz 2, barite 1 |
| saltpeter | 40 | 7.0% | 5-45 | saltpeter 3, diatomite 2, electrotine 2, alunite 1 |
| banded_iron | 30 | 5.2% | 20-40 | goethite 3, yellow limonite 2, hematite 2, gold 1 |
| beryllium | 30 | 5.2% | 5-30 | beryllium 3, emerald 2, thorium 2 |
| monazite | 30 | 5.2% | 20-40 | bastnasite 3, monazite 1, neodymium 1 |
| nether_manganese | 20 | 3.5% | 20-30 | grossular 3, pyrolusite 2, tantalite 1 |
| **molybdenum** | **5** | **0.9%** | 20-50 | wulfenite 3, molybdenite 2, molybdenum 1, powellite 1 |

**End** (layer `endstone`, total weight 160):

| Vein | Weight | Share | Y | Materials |
|---|---:|---:|---|---|
| end_bauxite | 40 | 25.0% | 10-80 | bauxite 2, ilmenite 1, aluminium 1 |
| end_magnetite | 30 | 18.8% | 20-80 | magnetite 3, vanadium magnetite 2, chromite 2, gold 1 |
| **naquadah** | 30 | 18.8% | 10-90 | naquadah, plutonium-239 (cuboid) |
| pitchblende | 30 | 18.8% | 30-60 | pitchblende, uraninite (cuboid) |
| **scheelite** | 20 | 12.5% | 20-60 | scheelite 3, tungstate 2, lithium 1 |
| sheldonite | 10 | 6.2% | 5-50 | bornite 3, cooperite 2, platinum 2, palladium 1 |

**Non-vein sources** [V recipe dump]: macerating **end stone** gives tungstate dust at **3.3%**; netherrack gold nugget
7.5%; deepslate thorium 1.5%; red granite (present in about half of overworld areas) U-238 at 0.25%.
**Bedrock fluids** [V]: Nether lava (w 65) and natural gas (w 35); overworld oil types and salt water; none in the
End. **Irrelevant here**: the pack removes the Fluid Drilling Rig recipes. No bedrock *ore* veins are defined, and the
Bedrock Ore Miner has no recipe.

### What a Nether area actually contains [V, 40 windows]
- Structures: fortress pieces 5/40 (12.5%), bastion 3/40 (7.5%), nether fossil 9/40. Blaze spawner 1/40.
  Nether wart 0/40 (fortress wart only grows in the stair rooms).
- Dominant biome: nether wastes 14, soul sand valley 12, crimson 6, basalt deltas 6, warped 2.
- Vanilla blocks (mean per area): netherrack 149k, nether quartz ore 1,112 (40/40), nether gold ore 380 (40/40),
  **ancient debris 14 (40/40)**, glowstone 33 (26/40), soul sand 3,300 (24/40), magma 1,900, blackstone 5,800.
- GT ores, share of areas with any block (mean blocks): sulfur 17/40 (339), **sphalerite 15/40 (50)**, nether quartz
  14/40 (314), quartzite 18/40, redstone 10/40, tetrahedrite/stibnite 12/40, beryllium/emerald/thorium 6/40,
  monazite/bastnasite/neodymium 4/40, certus 4/40, **molybdenum vein 1/40** (wulfenite 17, powellite 6, molybdenite 5).
  Because the window is not grid-aligned it touches 0 to 2 veins per area (not exactly 1, as in the overworld).

### What an End area would contain if reachable [V, 30 windows]
End stone 26/30. GT ores: magnetite/vanadium magnetite/chromite 6/30, bauxite/ilmenite 7/30, pitchblende/uraninite
6/30, **naquadah/plutonium 1/30**, **scheelite/tungstate 1/30**, sheldonite 1/30. Tungstate from macerated end stone:
~30,700 x 3.3% ≈ 1,000 dust per fully mined area [E].

### Which materials exist where (gated model: machines must be buildable) [V-model]
Seeds: OW = overworld areas + mobs + trader; N = + Nether veins/blocks (no fortress); NF = + fortress (blaze, wither
skull, so **nether star**); E = + End stone, End veins, chorus.

| Material | OW | +N | +N+fortress | +End | +N+End | All |
|---|---|---|---|---|---|---|
| tungsten, tungstensteel, tungsten carbide, HSS-G, RTM alloy | - | - | - | Y | Y | Y |
| molybdenum (also ultimet) | - | Y | Y | Y | Y | Y |
| indium (needs sphalerite) | - | Y | Y | - | Y | Y |
| nether star | - | - | Y | - | - | Y |
| nether quartz | - | Y | Y | - | Y | Y |
| iridium, osmium (PGS chain; the IV LCR step needs an EV hatch, so molybdenum) | - | Y | Y | Y | Y | Y |
| naquadah, enriched naquadah | - | - | - | Y | Y | Y |
| trinium | - | - | - | - | Y | Y |
| naquadria, europium, americium, darmstadtium, tritanium, duranium, neutronium (fusion products) | - | - | - | - | - | Y |
| netherite | - | Y | Y | - | Y | Y |
| gallium, vanadium, boron, antimony, Ti, Cr, Pt, Pd, Ru, Rh, Nd, Sm, Y, Ba, Nb, Ta, Li, Be, Th, U-238, Pu-239, quartzite, certus, ender pearl/eye, glowstone, blaze powder | Y | Y | Y | Y | Y | Y |

Cross-check with the research doc:
- Tungsten: confirmed absent from the overworld (`scheelite`/`tungstate` are End-only), **but End stone itself yields
  tungstate (3.3%)**, so any End terrain is a tungsten source.
- Naquadah: confirmed End-only. Trinium comes from the naquadah chain but also needs the Nether (the model needs both).
- Uranium and plutonium are **not** End-only: U-238 comes from red granite (0.25%) and Pu-239 from U-238
  centrifuging. They are slow but in the overworld. Pitchblende/uraninite are End-only.
- Platinum group: Pt/Pd/Ru/Rh are overworld via PGS (pentlandite, chalcopyrite). Ir/Os need the IV-tier rarest-metal
  step, so they are blocked in an overworld-only game by the EV hatch (molybdenum), not by ore.
- Europium: no ore. It is a fusion product, as the doc says.

### Tier progression by scenario [V-model]
Each line gives the highest tier where the hull, energy hatch, circuit and 20 core components are all buildable.

| Scenario | Highest complete tier | First thing missing |
|---|---|---|
| A: overworld only (mined + mobs + wandering trader) | **HV** | EV energy hatch (MPIC chip needs an EV cutter, which needs an ultimet buzzsaw: **molybdenum**), EV field generator (**nether star**), EV cutter (molybdenum) |
| B: A + Nether, no fortress | **EV** (except the field generator) | IV: tungsten |
| B without the molybdenum vein | HV | same as A |
| C: B + fortress (nether star) | EV complete | IV: tungsten |
| D: A + End stone only | EV (no cutter or field generator), IV 13/20 | IV hatch (HPIC: **indium**), IV emitter/sensor (quantum star: **nether star**) |
| E: A + all End | EV (no field generator), IV 14/20 | as D |
| F: Nether (no fortress) + End | **IV** (no emitter, sensor or field generator) | quantum star (nether star) blocks the IV sensor/emitter, which blocks the Assembly Line and everything LuV+ |
| G: everything | **UV** | none |
| H: G minus the naquadah vein | LuV | ZPM: naquadah |

**Minimal unlock set for UV [V-model]:** the overworld plus (1) **end stone** (tungsten), (2) **one nether star** (a Wither:
3 wither-skeleton skulls from fortress pieces + 4 soul sand), (3) **sphalerite** (Nether sulfur vein: indium), (4)
**molybdenum** (Nether molybdenum vein, 0.9% of Nether veins, or the End scheelite vein), (5) the **naquadah vein**.
Without (5) the game stops at LuV, without (2) at IV, and without (1) or (3) at EV.
The quantities (one nether star is enough for one quantum star, but each IV sensor/emitter needs one) are not
modelled.

### Material -> first tier it appears in a machine bill [V `ITEM_MATERIAL_INFO`, tier-prefixed items, tools excluded]
| Tier | Materials first needed (dimension-relevant ones in bold) |
|---|---|
| ULV | bronze, copper, iron, lead, magnetic iron, red alloy, rubber, tin, wrought iron |
| LV | battery alloy (**antimony**), brass, cobalt brass, diamond, **ender pearl** (field gen), gold, graphite, magnetic steel, manganese phosphide, polyethylene, **quartzite** (emitter/sensor), steel, zinc |
| MV | aluminium, cupronickel, electrum, emerald, **ender eye** (field gen), magnesium diboride (**boron**), PVC, silver, vanadium steel |
| HV | black steel, chromium, kanthal, magnetic neodymium, mercury barium calcium cuprate (**barium, mercury**), PTFE, red steel, stainless, titanium, tungsten carbide (fluid rig only) |
| EV | HSS-S, magnetic samarium, neodymium, **nether star** (field gen), nichrome, niobium-titanium, osmiridium, platinum, Rh-plated Pd, ruridit, silicone rubber, **tungstensteel** (rig), ultimet (**molybdenum**; cutter, rotor holder), uranium triplatinum |
| IV | graphene, HSS-G, **iridium**, **osmium**, RTM alloy, rose gold, samarium iron arsenic oxide, **tungsten**, vanadium gallium |
| LuV | blue steel, HSS-E, indium tin barium titanium cuprate (**indium**), niobium nitride, palladium, ruthenium |
| ZPM | **beryllium**, **europium**, **naquadah**, naquadah alloy, PBI, **trinium**, uranium rhodium dinaquadide, YBCO |
| UV | **americium**, **darmstadtium**, duranium, enriched Nq-trinium-europium-duranide, **naquadria**, **tritanium** |
| UHV | neutronium |

Not in bills but gating by recipe [V-model]: indium (IV energy hatch through HPIC), molybdenum (EV hatch through
MPIC/EV cutter), nether star (IV emitter/sensor through quantum star, so the Assembly Line), gallium (MV circuits),
vanadium (MV hatch through ULPIC).

## 3. Vanilla dimension-locked items in GT recipes [V recipe dump + V-model]

| Item | Natural source | GT consumers (tier) | Overworld substitute? |
|---|---|---|---|
| Nether quartz | Nether ore, piglin barter 4.4%, mason **buys** it, bastion chests | 4 recipes (comparator, granite/diorite alloying; engraving at HV). Not on the progression path | Quartzite and certus come from SiO2 by autoclave [V-model]; nether quartz itself only from its ore |
| Glowstone | Nether, witch drop, cleric (journeyman, block), wandering trader (block) | redstone lamp, glowstone plate cutter (LV), centrifuge | Yes: witches, cinnabar ore processing, traders |
| Blaze rod/powder | Fortress only | blaze powder: ender eye; `chemical_reactor/blaze_powder` (carbon + sulfur, **HV** 480 EU/t); `compressor/blaze_rod` | **Yes, GT synthesises it at HV** |
| Ender pearl | Endermen (overworld too), cleric master trade, trial-chamber and stronghold chests, barter 2.2% | LV field generator; voiding covers | Yes; also ProjectE `iron_ingot_to_ender_pearl` (philosopher's stone) |
| Ender eye | crafted (pearl + blaze powder) | MV field generator, HV emitter/sensor | via GT blaze powder (HV) |
| Nether star | Wither only (fortress skulls + soul sand) | EV field generator; **quantum star** (chemical bath), so IV emitter/sensor, so the Assembly Line and LuV+ | **None.** Implosion only re-forms star dust |
| Netherite/debris | Ancient debris (14 per Nether area [V]), bastion chests | Only smithing upgrades of GT tools/armour | not needed for progression |
| End stone | End | slabs/stairs; macerating it gives **tungstate 3.3%** | none |
| Chorus, shulker shell, dragon egg, dragon breath, elytra | End | purpur/end rod/shulker box only; dragon egg and breath have no GT use | not needed |
| Ghast tear, magma cream, nether wart, soul sand | Nether | separation recipes, end crystal (LV), decorative items | not needed (magma cream also comes from overworld slimes + GT) |

## 4. Other in-game sources [V source/data]

### Villagers and the wandering trader (`VillagerTrades`)
- Cleric: L3 sells **glowstone** (block, 4 emeralds), L4 sells **ender pearl** (5 emeralds), L5 *buys* nether wart.
- Mason: L4 *buys* quartz; L5 **sells quartz block and quartz pillar** (1 emerald). A quartz block macerates to
  nether-quartz dust, so this is a non-Nether quartz source.
- Wandering trader: glowstone (block), slime ball, sand, gunpowder, all dyes (**brown dye**: cocoa is jungle-only, and
  the pack removed the stone-dust "metal mixture" route; brown dye is needed for the brown lens, so MPIC, so the EV
  energy hatch [V-model]), saplings, coral, packed/blue ice. Traders spawn near players in the overworld.
- Villages are rare in a Run: 6/250 areas (2.4%, ≈3.6% of non-ocean areas) [V]. Zombie villagers can be cured
  without the Nether: GT makes blaze powder at HV for a brewing stand, and igloo basements hold a weakness potion and
  a golden apple [E].
- **Risk (already noted in the research):** emerald trades create EMC/value from renewables.

### Chest loot and structures (`loot_table/chests`, structure scan of 250 areas)
P = share of areas where **any piece's bounding box overlaps the area**, which overcounts real content. Block-based
lower bounds from the research's 124 areas: trial spawner/vault blocks in 1%, rails 23%, chests 27%, spawners 29%
[V]. Similarly, 0/40 Nether areas had nether wart and 1/40 had a blaze spawner. Fortress "overlap" therefore often
means only a corridor.

| Structure | P(overlaps 3x3 area) [V] | Relevant loot |
|---|---:|---|
| Mineshaft | 29% | diamond, gold, iron |
| Trial chambers | 7.2% | **ender pearl** (corridor), diamonds, emeralds; breeze rods |
| Village (plains seen) | 2.4% | emeralds, obsidian (weaponsmith); villagers |
| Shipwreck, ocean ruins, monument, buried treasure | ≤1.6% each | emeralds, diamonds, prismarine |
| Ancient city, trail ruins, jungle temple, ruined portal | ≤0.8% each | ruined portal: obsidian, flint and steel, gold |
| Stronghold | 0/250 | ender pearls; the End portal |
| Nether fortress (Nether area) | 12.5% | nether wart, obsidian, gold, diamond; **wither skeletons, blazes** |
| Bastion (Nether area) | 7.5% | **ancient debris / netherite scrap**, quartz, glowstone (stable) |
| End city (End area) | 1.6% | shulkers, elytra (unreachable anyway) |

### Piglin bartering (`gameplay/piglin_bartering`)
ender pearl 2.2%, quartz 4.4%, soul sand 8.7%, obsidian 8.7%, crying obsidian 8.7%, string, leather, fire charge,
gravel, blackstone, nether brick, spectral arrow, potions. Bartering needs piglins (crimson forest / nether wastes)
and gold. **No glowstone, no blaze items, no nether star.**

### Non-mining natural sources for each dimension-locked or missing material
| Material | Non-mining source in a Run? |
|---|---|
| Tungsten | none (End stone or End scheelite vein) |
| Molybdenum | none |
| Indium (sphalerite) | none |
| Naquadah (and trinium) | none |
| Nether star | none (the Wither needs fortress skulls) |
| Nether quartz | mason L5 quartz blocks; piglin barter; bastion chests |
| Glowstone | witches, cleric, wandering trader; GT from cinnabar |
| Ender pearl | endermen, cleric L4, trial chambers, ProjectE conversion |
| Blaze powder | GT chemical reactor at HV |
| Netherite | bastion chests (Nether) |
| Europium, americium, naquadria, tritanium, darmstadtium | none: fusion outputs (need naquadah and the rest above) |

## 5. Overworld GT vein frequency per Run area

With Run areas centred on GT grid chunks, each layer holds exactly one grid vein, so **P(vein dominant) = weight /
layer total** [V `ore_vein` weights; layer totals stone 860, deepslate 340]. Neighbouring grid veins 48 blocks away
spill in, so P(any block of a material) is higher [V, the research's 124 areas]. Expected Runs to first meet = 1/P [E].

| Layer | Vein | P(dominant) | Materials | P(>=1 block) of key material [V] |
|---|---|---:|---|---|
| stone | iron | 14.0% | goethite, limonite, hematite, malachite | goethite 37% |
| stone | cassiterite / coal / garnet_tin / magnetite / mineral_sand | 9.3% each | tin+cassiterite / coal / cass. sand, garnet sand, asbestos, diatomite / magnetite, **vanadium magnetite**, gold / mineral sands, fuller's earth, gypsum | vanadium magnetite 12% |
| stone | copper_tin | 5.8% | chalcopyrite, zeolite, cassiterite, **realgar** | realgar 15% |
| stone | salts | 5.8% | rock salt, salt, **lepidolite, spodumene** | spodumene 6% |
| stone | apatite, galena, garnet, lubricant, nickel, oilsands | 4.7% each | apatite/TCP/pyrochlore; galena/silver/lead; garnets/amethyst/opal; soapstone/talc/glauconite/pentlandite; garnierite/nickel/cobaltite/pentlandite; oilsands | galena 12%, nickel 6%, pentlandite 13% |
| deep | copper | 23.5% | chalcopyrite, iron, pyrite, copper | chalcopyrite 61% |
| deep | redstone / sapphire | 17.6% each | redstone, **ruby**, cinnabar / almandine, pyrope, sapphire, green sapphire | ruby 21% |
| deep | diamond / lapis | 11.8% each | diamond, graphite, coal / lazurite, sodalite, lapis, calcite | diamond 15% |
| deep | manganese / **mica** / olivine | 5.9% each | grossular, spessartine, pyrolusite, tantalite / kyanite, mica, **bauxite**, pollucite / bentonite, magnesite, olivine, glauconite | bauxite 15%, tantalite 7% |

Overworld materials that come from one vein only, so are "rare per Run" rather than absent [V-model, single-vein
knockouts]:
- **gallium** (and rutile, so titanium early): mica vein, 5.9%. Gates MV circuits.
- **vanadium**: magnetite vein, 9.3%. Gates the ULPIC, so the MV energy hatch.
- **boron**: salts vein, 5.8%. Gates magnesium diboride, so the MV field generator.
- **barium** and **antimony**: copper_tin vein, 5.8%. Barium is in the MBCC wire, so the HV field generator.
  Antimony is in battery alloy, so the LV battery hull.
- **ruby/cinnabar**: the redstone vein (17.6%) gates HV circuits in the model. Through the HV-made blaze powder it also
  gates the ender eye and the MV field generator.
- **galena** (5% stone) is required together with Nether sphalerite for indium.
- Vanilla emerald ore: in 23% of areas (mountains), needed for beryllium in the overworld [V].

**Knowledge only helps items that have EMC.** ProjectE can learn and transmute only valued items, and every GT
ore, dust and ingot named here has **0 EMC** today: gallium, vanadium, boron, antimony, tungsten/tungstate,
molybdenum/wulfenite, indium/sphalerite, naquadah, scheelite and quantum star [V econ dump]. So these veins must be
present *in the Run that needs them*: P(vein) applies to every Run, not just once. They would become cumulative
("find once", ≈1/P Runs: gallium/boron/antimony ~17, vanadium ~11 [E]) only if the pack prices them.

The vanilla dimension items mostly *do* have EMC [V]: **nether star 139,264**, **end stone 1**, netherrack 1, quartz 256,
glowstone dust 384, ender pearl 1,024, blaze rod 1,536, ghast tear 4,096, shulker shell 2,048, netherite scrap 12,288,
dragon egg 262,144. Wither skeleton skull, ancient debris and dragon breath have 0. Consequences [E]:
- **One Wither, ever**, would let a player transmute nether stars for EMC from then on.
- **One end stone** learned gives unlimited transmuted end stone at 1 EMC each. Macerated, it yields tungstate at 3.3%,
  so knowing end stone is a renewable overworld tungsten source.

### Nether-star quantity [V recipes + loot table, E arithmetic]
- `chemical_bath/quantum_star`: 1 nether star + 1,250 mB radon gives 1 quantum star (HV).
- The IV sensor, IV emitter and IV field generator each take 1 quantum star. LuV/ZPM sensors, emitters and field
  generators, fusion MK3 and the gravi star also use them.
- `assembly_control_casing`: 1 IV sensor + 1 IV emitter make 2 casings. A 5-slice Assembly Line therefore needs 3
  sensors + 3 emitters = **6 nether stars = 6 Withers = 18 skulls**.
- Wither skeleton skull: 2.5% (`random_chance_with_enchanted_bonus`, Looting adds +1%/level from 3.5%), so ~720
  kills without Looting or ~330 with Looting III.
- Wither skeletons spawn only on fortress pieces inside the 48x48 Nether area, and only 12.5% of areas overlap a
  fortress at all. Without EMC transmutation of nether stars, **this, not tungsten, is the LuV wall**.

## Caveats
- The model checks existence and buildability, not quantities, energy or time. Chanced byproducts (end stone 3.3%,
  red granite 0.25% U) count as available.
- Multiblock rule "hatch tier >= recipe tier - 1" (two hatches) and the steam rule are approximations of GT logic.
  Under a strict rule, the IV rarest-metal LCR step (Ir/Os) needs an IV hatch (indium) instead of an EV hatch
  (molybdenum). Both are Nether-gated, so the headline holds either way.
- Structure probabilities come from one seed. Small counts (≤ 6) are ±50%. Ocean-centred areas are included in the
  250 (the mod re-picks them), so land-only rates are about 1.5x for land structures.
- Nether windows: one seed, 40 samples.
