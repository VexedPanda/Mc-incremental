# EMC economy: one Run's yield vs. the cost of GT tiers

Question (pack owner): *"Is mining all 9 chunks enough EMC to make endgame viable? What do endgame machines cost, and how much EMC do the chunks give?"*

Legend: **[V]** measured on the real pack (headless server, GTCEu 8.0 snapshot 8602baa, ProjectE PE1.1.0, pack config from `integration/poc1-pack` incl. current `custom_emc.json`) or read in source. **[E]** estimate or assumption. The goal is order-of-magnitude accuracy.

## TL;DR

- **One fully mined and processed Run gives about 7M EMC (smelt/drop) to 10M EMC (GT macerator route). The 10th–90th percentile range is 5–14M.** [V counts, E processing] About 60% comes from *vanilla* ores (diamond and lapis above all), about 25% from the two GT veins, and about 10% from bulk stone. Trees and the surface are negligible.
- **LV to EV is cheap:** each tier's kit costs 0.4–1.6M EMC, so **IV costs less than one Run** (~8M cumulative) in EMC terms.
- **The wall is not EMC but existence.** From IV upward, recipes need materials that **no overworld ore yields, not even as a byproduct**: tungsten (IV hull and tungstensteel), uranium/plutonium, naquadah, trinium, europium and the fusion outputs. With the Run confined to a 3×3 overworld area, a player never *finds* these. So they never get Knowledge of them, and no EMC balance can buy them. [V source]
- **If those materials were obtainable** at the assumed values below, LuV needs ~9–12 Runs of saved-up EMC, ZPM ~30–40, UV ~90–125. These totals depend directly on the EMC prices *the pack sets* for materials that don't exist in a Run. So they are a design dial, not a fact.
- **Net gain per Run is lower today:** under current values nothing past LV can be transmuted back, and the sweep refunds the rebuilt kit at 0. So each Prestige eats the kit (~4M by EV), and the *net* gain per Run is ~3–6M rather than 7–10M. Compounding is roughly halved until GT items are valued.
- **Today almost nothing past LV has an EMC value:** 9 of 1,297 tiered GT items, and 244 of 8,793 GT items overall, are non-zero [V]. Building an MV+ machine therefore turns valued metal into a 0-EMC item. Unless the prestige sweep values items some other way, it would refund **0** for it. The "machines are a refundable float" design only works once machine values exist.
- **About 45% of GT ore blocks in a Run are unvalued** (kyanite, almandine, graphite, oilsands, bauxite, mica, salts, ...) [V].

## 1. EMC obtainable from one Run (3×3 chunks, y −64..320)

### Method [V]
The dump script `emc-economy/zz_econ.js` runs as a KubeJS server script in a copy of the smoke-test server. The script:
- force-generates Run areas, i.e. 3×3 chunks centred on a GT grid chunk (chunk x, z multiples of 3; vein centre = middle of that chunk ±12 blocks, `OreVeinUtil.getVeinCenter`);
- counts every block state with `PalettedContainer.count`;
- dumps ProjectE's EMC for all 10,235 items and GT's recycling material map (`ItemMaterialData.ITEM_MATERIAL_INFO`);
- dumps 8,971 recipes (crafting, assembler, circuit assembler, assembly line, laser engraver, cutter, forming press, chemical reactor, EBF, fusion).

Two seeds, 124 Run areas (seed 1: 49 areas over 2 regions; seed 2: 75 areas over 3 regions of 5×5 adjacent grid cells). Ocean areas were *not* excluded (the Prestige skips oceans). Neighbouring grid veins spill into a Run (they sit 48 blocks away and have radius ~12–32), and the counts include that spill, so the per-Run figures are true expectations.

### Per-Run EMC, mean over 124 areas

| Source | Blocks / Run | EMC basic (smelt/drop) | EMC GT route (macerate 2×) | Notes |
|---|---:|---:|---:|---|
| Bulk blocks (stone→cobble 1, cobbled deepslate 2, tuff 4, **granite/diorite/andesite 16**, calcite 32, dirt/gravel; also ancient-city sculk ~30k avg, which needs Silk Touch) | ~870k | **0.92M** (0.6–1.4M) | same | Not tiny: the 16-EMC stones give ~0.43M. Deepslate 0.24M, stone 0.12M. [V] |
| Vanilla ores (scattered baseline, `removeVanillaOreGen=false`) | copper 1,390, coal 1,248, iron 733, redstone 325, gold 233, lapis 224, **diamond 223**, emerald 3 | **4.7M** (3.0–6.7M) | **6.2M** | Diamond (223 × 8,192 = 1.8M) and lapis (224 × 6.5 × 864 = 1.3M) dominate. ~25 diamond ore/chunk. [V counts, E drop averages] |
| GT veins (stone + deepslate layer, incl. neighbour spill) | ~4,980 | **1.6M** (0–7.6M) | **3.2M** | 2,257 of the 4,977 blocks (45%) are unvalued materials → 0. [V] |
| Surface logs (one-off) | ~140 | 4k | 4k | Negligible. |
| **Total** | | **7.2M** (p10 5.1M, median 7.0M, p90 9.2M, max 13.4M) | **10.4M** (p10 6.7M, median 10.2M, p90 14.3M, max 22.6M) | |

Processing assumptions [E, from `OreRecipeHandler` V]:
- 1 ore block gives 1 raw ore.
- Smelting raw ore gives `oreMultiplier` × the direct-smelt result. Examples: chalcopyrite→Cu, goethite/hematite/magnetite/pyrite/mineral sands→Fe, galena→Pb, garnierite/pentlandite→Ni, cassiterite (×2)→Sn, GT redstone ×5, GT lapis ×6, GT coal ×2.
- Macerating gives 2× crushed (plus a 14% byproduct chance, not counted).
- Vanilla drops without Fortune: copper 3.5 raw, redstone 4.5, lapis 6.5.
- **Upside not counted:** Fortune III on vanilla diamond/lapis/coal/redstone adds ~**+3.9M**, and byproducts add maybe +10% on the GT part, for a ceiling of ~**14M/Run**. **[U]** I have not verified whether Fortune multiplies *raw-ore* drops (vanilla iron/gold/copper and GT ore blocks) in this pack: GT's `ToolHelper` builds ore-bonus functions, but a bonus in `MixinHelpers` is commented out. If it does, Fortune × macerate is ≈4× on those and the ceiling is nearer **~20M**.
- All figures assume **100% of 885k blocks are excavated**, which in practice means GT miners. A hand-mined Run will be a fraction of this.

Current ProjectE values [V, from the dump]: iron 256, copper 128, tin 256, lead/silver/zinc/steel 512, nickel/aluminium 1,024, gold 2,048, platinum 4,096, **osmium 512**, ruby/sapphire 2,048, diamond 8,192, emerald 16,384, lapis 864, redstone 64, coal 128. **0 EMC:** every other GT ingot/gem/dust (160 ingots, 101 gems, 342 dusts), including stainless, titanium, chromium, tungsten, iridium, palladium, invar, electrum, cobalt, silicon, graphite, diamond *dust*, and all raw/crushed ores.

### Per GT vein (dominant vein in the layer; mean over the areas where it was dominant)

| Layer | Vein (weight) | Areas | Ore blocks in layer | EMC basic | EMC GT route | What pays |
|---|---|---:|---:|---:|---:|---|
| stone | iron (14%) | 18 | 1,545 | 0.37M | 0.74M | Fe 256 |
| stone | cassiterite (9%) | 9 | 2,112 | 0.71M | 1.4M | Sn ×2 |
| stone | coal (9%) | 2 | 437 | 0.11M | 0.22M | coal ×2 (small sample) |
| stone | garnet_tin (9%) | 13 | 4,954 | 1.45M | 2.9M | cassiterite sand ×2 |
| stone | magnetite (9%) | 8 | 2,574 | 1.1M | 2.2M | Fe + Au |
| stone | mineral_sand (9%) | 11 | 2,890 | 0.55M | 1.1M | →Fe |
| stone | copper_tin (6%) | 7 | 1,615 | 0.26M | 0.53M | Cu 128 is cheap |
| stone | salts (6%) | 4 | 2,749 | 0.06M | 0.12M | **mostly unvalued** |
| stone | galena (5%) | 12 | 2,367 | 1.15M | 2.3M | Pb/Ag 512 |
| stone | **nickel (5%)** | 5 | 4,524 | **3.7M** | **7.4M** | Ni 1,024 (best stone vein) |
| stone | lubricant / apatite / garnet / oilsands (5% each) | 6–10 | 1,500–1,900 | 0.03–0.19M | 0.07–0.39M | **mostly unvalued** |
| deep | copper (24%) | 30 | 2,153 | 0.37M | 0.75M | Cu/Fe |
| deep | redstone (18%) | 21 | 3,497 | 2.2M | 4.3M | redstone ×5, ruby 2,048 |
| deep | sapphire (18%) | 21 | 2,039 | 0.40M | 0.81M | sapphire only; almandine/pyrope = 0 |
| deep | **diamond (12%)** | 11 | 2,739 | **2.2M** | **4.5M** | ~270 diamonds; graphite = 0 |
| deep | **lapis (12%)** | 11 | 2,017 | **2.3M** | **4.6M** | lapis ×6 |
| deep | mica / olivine / manganese (6% each) | 7–14 | 900–3,800 | ≈0 | ≈0 | **unvalued** |

Weight-averaged over vein weights: stone layer ~0.7M, deepslate layer ~1.1M (basic), so ~1.8M/Run vs. 1.6M observed. Best case: nickel + lapis/diamond ≈ 6M basic / 12M GT. Worst case: salts/oilsands + manganese/olivine ≈ 0.1M. A single Run's GT contribution varies about 50×. [V, small per-vein samples: ±30%]

**Renewables [E, rough]:** mob drops ~30–200 EMC/mob (a dark-room farm in 48×48 maybe 20–50k EMC/h); tree/crop farms ~5–20k EMC/h. These matter at LV–EV and are irrelevant at LuV+. **Risk:** villager trades. A farmer buys 20 wheat (~480 EMC) for 1 emerald (16,384 EMC). If trading isn't capped, it becomes the dominant income and makes this whole analysis moot (ADR-0005 says exploitable trades are fixed individually; this is one).

## 2. EMC cost of GT machines by tier

### Method
- **Machine material bills [V]:** GT's own recycling data (`ITEM_MATERIAL_INFO`). It gives each machine's metal content but excludes circuits.
- **Circuits and assembler/assembly-line parts:** costed recursively from the dumped recipes, taking the cheapest recipe and valuing leaf tags (plates, foils, fine wires, fluids at 144 mB/ingot) by material.
- **Alloys:** valued from their GT `components` (e.g. stainless = (6 Fe + Cr + Mn + Ni)/9; HSS-S = (6 HSS-G + 2 Ir + Os)/9), with O/H/N/Cl/F = 0.
- **Materials ProjectE leaves at 0 need a price.** I used this explicit ladder [E] (EMC per ingot/dust):

| Material | Assumed EMC | Material | Assumed EMC |
|---|---:|---|---:|
| Mn, Ba | 512 | Cr, Co, Be, Th | 1,024 |
| Ti, V, Mo, Nd, Y, In | 2,048 | W, Nb, Ta, Sm, Pd (Pt default is 4,096) | 4,096 |
| Rh, Ru | 8,192 | Ir, **Os (raised from the PE default 512)**, Eu, Pu | 16,384 |
| Naquadah, Am | 32,768 | Enriched Nq, Trinium, Duranium | 65,536 |
| Naquadria, Tritanium, Darmstadtium | 131,072 | Neutronium | 524,288 |
| Rubber / PE / PTFE / PBI | 64 / 64 / 256 / 1,024 | Carbon, graphene | 64, 128 |

  The resulting alloys: stainless 455, invar 512, kanthal 768, electrum 1,280, tungstensteel 2,304, Rh-plated Pd 5,120, HSS-S 6,846, ruridit 10,923, osmiridium 16,384, naquadah alloy 36,864.
- Few estimated leaves: raw crystal chip 8k, quantum star 150k, petri dish 256.
- Energy (EU) and process consumables (acids, solder lost, etc.) are **not** included; see §3.

### Cost per tier (ladder scenario)

| Tier | Cheapest circuit | Hull | Macerator (representative single-block) | Kit: 16 single-block machines | Key multiblock | Kit + multiblock | Cumulative |
|---|---:|---:|---:|---:|---|---:|---:|
| Steam | – | – | LP steam macerator 18k (pack value 12k) | ~50–80k | – | ~0.07M | 0.07M |
| LV | 95 (pack: basic circuit 2,048) | 4.6k | 18.6k | 0.30M | EBF + 16 cupronickel coils + casings/hatches **0.15M** | 0.44M | 0.5M |
| MV | 182 | 8.6k | 30.6k | 0.49M | – | 0.49M | 1.0M |
| HV | 791 | 5.9k* | 74k | 1.19M | (cleanroom ~0.1M) | 1.2M | 2.2M |
| EV | 2.5k | 17.7k | 98k | 1.56M | – | 1.6M | 3.8M |
| IV | 7.1k | 23.2k | 114k | 1.83M | **Assembly Line (5 slices) 2.8M** | 4.6M | **8.4M** |
| LuV | 20k | 45k | 437k | 7.0M | **Fusion MK1 71M** (95 casings × 614k, 16 LuV energy hatches, 4 coils; superconducting coil 976k, of which trinium 3,456 mB ≈ 1.6M) | 78M | **86M** |
| ZPM | 58k | 299k | 1.2M | 19.6M | Fusion MK2 187M | 206M | **292M** |
| UV | 171k | 1.05M | 6.4M | 103M | Fusion MK3 505M | 608M | **~900M** |
| UHV | 2.1M | 4.2M | – | (16 hulls 67M) | – | ≥100M | **≥1G** |

\*The HV hull is cheaper than MV because stainless (455) is valued below the pack's aluminium (1,024). This is an artefact of the current aluminium value.

Notes:
- Raw circuit material content is small: LV ~100–400, IV 7–17k, UV ~170k. The pack's hand-set basic circuit (2,048) and good circuit (8,192) are ~5× their recipe content.
- The macerator kit overweights diamond (grinding heads; diamond is 30–55% of the LV–EV kit cost). Other machine types are ~20–40% cheaper.
- Multiblock structure counts are from the `GTMultiMachines` patterns [V]: EBF 16 coils + 11 casings; fusion 48+31+48 casing positions, 16 energy hatches, 4 coils.

**Which materials dominate (recycling bill, ladder prices) [V bills, E prices]:**

| Tier | Top materials by cost | Share needing a non-overworld material |
|---|---|---:|
| LV–EV | diamond, steel, nickel, aluminium, gold, titanium | 0% |
| IV | **tungsten 62%**, iridium 11%, platinum 7% | **62%** (tungsten) |
| LuV | iridium 35%, ruthenium 19%, palladium 10%, tungsten 10%, + trinium in coils | 10–40% |
| ZPM | europium 29%, naquadah 24%, iridium 15%, trinium 14% | **73%** |
| UV | tritanium 32%, darmstadtium 32%, naquadah 13%, americium 12% | **96%** |
| UHV | neutronium ~100% | 100% |

## 3. Comparison: Runs needed, and what blocks progress

EMC carries over and the sweep refunds builds at full value, so machines are a **float**, not a sink. The Runs needed are roughly *cumulative kit cost ÷ EMC per Run*. That assumes machines have EMC values (they mostly don't yet) and ignores consumables.

| Target | Cumulative EMC | Runs @ 7.2M (basic) | Runs @ 10.4M (GT route) | Runs @ ~14M (Fortune + byproducts) | Blocking material (must be *found* once for Knowledge) |
|---|---:|---:|---:|---:|---|
| Steam–LV | 0.5M | <0.1 | <0.1 | <0.1 | none |
| MV–EV | 1–4M | 0.2–0.5 | 0.1–0.4 | <0.3 | none. Ti (rutile from bauxite), Cr (ruby), Pt/Pd (PGS from chalcopyrite/pentlandite) all have overworld sources [V] |
| IV | 8.4M | 1.2 | 0.8 | 0.6 | **tungsten: no overworld ore or byproduct** (scheelite/tungstate are End-only veins) [V] |
| LuV | 86M | 12 | 8 | 6 | tungsten; **trinium** (naquadah chain, End-only) for superconducting coils. Ir/Os/Ru/Rh are OK via PGS |
| ZPM | 292M | 41 | 28 | 21 | naquadah/trinium (End-only ore). Europium has no ore source (the rare-earth chain gives Ce/Nd/La/Cd/Sm/Y); it is a fusion product, so it needs MK1 fusion (and its End-only inputs) first [V] |
| UV | ~900M | 125 | 87 | 64 | naquadria, tritanium, darmstadtium, americium (fusion outputs, i.e. a working LuV/ZPM fusion first) |

Things that add to the totals (not modelled) [E]:
- **Energy is a small sink; consumables a modest one.** Diesel gives 480 EU/mB in a combustion generator [V, `FuelRecipes`: 1 mB, 15 t at 32 EU/t]. At 768 EMC/bucket that is ≈0.0016 EMC/EU. So an EV-era EBF batch (~1.5M EU) costs ~2.4k EMC, and a fusion start (10M EU) ~16k. Chemistry consumables (PGS needs nitric acid and aqua regia; solder, lubricant) add maybe a few % to the totals [E].
- **Per-Run rebuild time and effort:** a full 885k-block excavation per Run.

**Bottom line.** EMC volume is fine up to IV (about one Run). LuV needs ~10 Runs and ZPM–UV needs 30–125 Runs at the assumed prices. That is long but not absurd for an incremental pack. The real blockers are:
- **(a) existence/Knowledge:** tungsten and the naquadah line never appear in a 3×3 overworld Run;
- **(b) zero EMC values:** for nearly every GT intermediate and machine, which breaks both transmutation and the sweep refund.

A Nether/End policy is undefined in the docs. As far as I know, vanilla's border delegate scales the Nether border to 1/8, so a Nether portal would lead into a ~6×6-block area; this is unverified. Either way, the Run design effectively excludes both dimensions.

## 4. Options, and their effect on the numbers

| Option | Effect on EMC/Run | Effect on endgame |
|---|---|---|
| **Price the non-existent materials** (W, Nq, trinium, Eu, Am...) | none | The single biggest dial. Halving the ladder above Pt halves LuV–UV Run counts (e.g. UV ~45–60 Runs). Players still need *one* unit to learn each, so pair it with a source (below). |
| **Seed Knowledge** for End-only materials (villager/wandering-trader trades, loot, quest reward, a Meta unlock per Prestige count) | none | Removes the IV and ZPM existence walls. EMC then decides the pace. |
| **Value all GT items** (generate `custom_emc.json` from GT recycling bills + recipe costing, as done here) | sweep refunds become real | Required for the "float" model. Without it, MV+ machines are EMC sinks that refund 0 (to be confirmed against the prestige mod's sweep valuation). |
| **Value the unvalued ores** (kyanite, almandine, graphite, bauxite, salts, oilsands...: 45% of GT ore blocks) at e.g. 128–256 | +0.3–0.6M (basic), +0.6–1.2M (GT) | Raises the floor of bad Runs (salts/mica/olivine Runs ≈ 0 today). Small vs. LuV+. |
| **`oreVeinGridSize` 3→2** | ~2.25 veins per layer per Run: GT part ×2.25 → total ~9.2M basic / ~14M GT (+28–35%) | Also makes the per-Run lottery less swingy. |
| **Larger Run area** (5×5 chunks centred on a grid point) | linear in area: ~2.8× → ~20M basic / ~29M GT | LuV ~3–4 Runs, UV ~30–45. Costs performance (#46 view distance) and more digging. |
| **Better processing** (GT full chain, Fortune III on vanilla gems) | 7.2M → 10.4M → ~14M | Already in the tables. It is the natural progression reward, so the ceiling is ~2× basic. |
| **Meta progression** (e.g. +X% EMC on the sweep or on burning ores per Prestige; permanent Knowledge) | multiplicative | Compounding: +10%/Prestige halves Runs to UV (~90 → ~30). |
| **Cap renewables/trades** (villager emerald loop) | prevents runaway | Without it, trading likely dwarfs mining and endgame becomes trivial. |

## Uncertainty and reproduction

- **Ore counts [V]:** 124 areas, 2 seeds, regions of adjacent cells (correlated); ±15% on means. Per-vein rows rest on 2–30 samples (±30%). Vanilla ore counts include every block in the 48×48×384 column (a full excavation).
- **Prices [E]:** every number past EV scales with the ladder in §2, which I chose by "rarity × iron". It is not derived from any source. The machine bills (what and how much) are [V].
- **Not modelled:** consumables in detail, multiple copies of machines, cleanroom/data-hatch research, loot chests. Ancient-city sculk (catalyst 8,040 EMC; ~30k/area average) *is* inside the bulk figure.
- **Scripts:** `emc-economy/zz_econ.js` (dump; KubeJS server script); `emc-economy/ana/{areas,veins,cost,recipes,tiers,breakdown}.py` (analysis); raw dumps not committed (regenerate with the dump script).
- **Re-run:** `python3 ana/areas.py dump1.txt dump2.txt`, `python3 ana/veins.py dump1.txt dump2.txt`, `python3 ana/tiers.py ladder|current`.
