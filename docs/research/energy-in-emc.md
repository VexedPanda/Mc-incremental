# Energy in EMC (#64)

Should a GT recipe's energy (EU/t × duration) count towards its outputs' EMC? Research only: nothing in the Pack or
the Prestige mod changes. Scripts and outputs are in `emc-pricing/` (see "Reproduce" below).

## Recommendation

**Don't count energy in EMC for now.** Count it only if #25 makes power cost EMC (or removes the cheap generators); in
that case, revisit with this setup.

- **Generation in GT 8.0 is too cheap for energy to matter.** EU can't safely be worth more than its cheapest
  generation. With the owner's time term included, that is about 5 × 10⁻⁵ EMC/EU. At that price only 5 of the 181
  in-game exploits close, and the late-tier floors are still needed.
- **A price that would close the #63 loops creates new loops.** The median loop needs about 0.04 EMC/EU to close. At
  that price every boiler mints EMC: a large tungstensteel boiler on dried kelp makes 2,560 EMC/s (9.2 M per hour).
- **The owner's time term can't be raised to close the gap.** Time costs the player no EMC, so any EMC price on time is
  minted, at exactly that rate, by every generator. The time term has to stay below the audit's noise floor (5 EMC/s
  per machine).
- **Close #63 groups 1, 2, 3 and 5 by pricing or acceptance, as #63 planned.** Keep #59's floors.

## 1. The EU price

EU price for a generator = (fuel EMC + time cost) ÷ EU made, per the owner's request. EU is fungible across tiers:
cables and transformers carry LV-made EU to an IV machine. So the price at tier *t* is the cheapest generator
available by *t*, and a pump-safe schedule can only stay flat or fall as the tier rises. `emc-pricing/eu_price.py`
(output: `eu_price.txt`) lists 157 generator and fuel pairs:

- **Recipe generators:** EU = output EU/t × duration, from a new dump, `dump_eu.js` → `eu.txt.xz`.
- **Boilers:** steam rates from GT 8.0's own code (`SteamBoilerMachine`, `LargeBoilerMachine`, `*BoilerLogic`, and
  the `gtceu.yaml` defaults), at 2 mB of steam per EU.
- **Solar covers:** `V[tier]` EU/t in daylight, assumed 50% of the time.
- **Values:** the dump's EMC values.

Fuel cost per EU for some of the generators (EMC/EU, fuel only):

| Generator, fuel | EU/s | Fuel only | + generator over 100 h | over 10 h | over 1 h |
|---|---:|---:|---:|---:|---:|
| LP solar boiler (free) | 30 | 0 | 3.3e-4 | 3.3e-3 | 0.033 |
| ULV solar panel cover (free) | 80 | 0 | 1.9e-4 | 1.9e-3 | 0.019 |
| Large tungstensteel boiler, dried kelp block (IV) | 64,000 | 2.8e-6 | 1.3e-4 | 1.3e-3 | 0.013 |
| Large steel boiler, dried kelp block (MV) | 18,000 | 1.0e-5 | **4.9e-5** | **4.0e-4** | 3.9e-3 |
| Large bronze boiler, dried kelp block (LV) | 8,000 | 2.3e-5 | **6.4e-5** | 4.4e-4 | 4.2e-3 |
| Large bronze boiler, lava | 8,000 | 7.1e-5 | 1.1e-4 | 4.9e-4 | 4.2e-3 |
| Gas turbine, butadiene / methane | 640 | 8.9e-5 | 1.2e-4 | **4.4e-4** | **3.6e-3** |
| Large bronze boiler, coal | 8,000 | 8.0e-4 | 8.4e-4 | 1.2e-3 | 4.9e-3 |
| Combustion generator, diesel (`emc-economy.md`) | 640 | 1.6e-3 | 1.7e-3 | 2.1e-3 | 6.9e-3 |
| LP solid boiler, coal | 60 | 0.027 | 0.027 | 0.027 | 0.034 |

Bold marks the cheapest generator by LV or MV and up, for each horizon.

Large boilers set the price. They burn a solid fuel for a quarter of its furnace time (`LargeBoilerLogic`) at every
tier, and make (max temperature) mB of steam per tick: 800 for bronze, up to 6,400 for tungstensteel. A
9-EMC dried kelp block therefore gives 160,000 to 1,280,000 EU. These rates come from the bytecode and haven't been
checked in game. Without large boilers the floor is the gas turbine at about 9 × 10⁻⁵, the same order.

**Valuing time.** The owner asked how to put a cost on time. These are the options:

- **(a) The generator's own EMC amortised over H hours of running.** The pricing above uses this. The generator's
  value includes the LV steam turbines a boiler needs, and the large boiler's casings, approximately.
- **(b) A flat EMC per second for each running generator.** This is (a) with rate = EMC ÷ H, but cut loose from what
  the generator cost. Big generators then win outright.
- **(c) A per-tier rate tied to what a player earns.** A Run banks about 65 M EMC, so this rate is thousands of EMC
  per second. That gives about 0.1 EMC/EU, which fails the pump check below by orders of magnitude.

In the Pack the Sweep refunds a generator at full value, so strictly no capital is used up. Time therefore costs the
player nothing in EMC, and whatever EMC rate time is given becomes free EMC: at price *p*, each generator gains at
most (its EMC ÷ H) per second. **I recommend (a) with H ≥ 100 h.** Then p ≈ 5 × 10⁻⁵ EMC/EU, every generator gains
under the audit's 5 EMC/s noise floor (the largest is 3.9 EMC/s, below), and the flat price is
`EMC_EU_PRICE=5e-5`. The fuel-only price is 0, since solar boilers are free.

## 2. Loops: what closes at each price

`emc-pricing/energy_sweep.py` (output: `energy_sweep.txt`) re-runs `generate.py`, `audit.py` and
`prestiges_per_tier.py` for each price. Prices are set with the new `EMC_EU_PRICE` flag; with it unset, every committed
output is unchanged.

The derived per-tier schedule (LV 6.4e-5, MV–HV 4.9e-5, EV and up 4.7e-5) falls with tier and stays within 30%, so
the flat 5e-5 row stands in for it.

The 181 in-game exploits from `audit.txt`, each paying its own EU with the in-game values otherwise unchanged. The
groups are assigned approximately, from recipe ids. Each cell is the number still open / of those, the number gaining
100+ EMC per run:

| EMC/EU | G1 cheap inputs | G2 ore chains | G3 refinery and fuel | G4 gas chemistry | G5 other | Total open |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 19 / 16 | 36 / 34 | 35 / 19 | 61 / 51 | 30 / 14 | **181 / 134** |
| 5e-5 (recommended) | 19 / 16 | 36 / 34 | 34 / 19 | 59 / 51 | 28 / 13 | **176 / 133** |
| 4e-4 (H = 10 h) | 19 / 16 | 33 / 31 | 32 / 18 | 59 / 51 | 28 / 13 | 171 / 129 |
| 0.0016 (diesel) | 19 / 16 | 28 / 26 | 30 / 15 | 54 / 44 | 23 / 12 | 154 / 113 |
| rising ×2 per tier (LV 0.0016) | 18 / 16 | 22 / 20 | 26 / 12 | 47 / 39 | 23 / 12 | 136 / 99 |
| rising ×4 per tier | 18 / 16 | 16 / 14 | 21 / 11 | 44 / 34 | 23 / 12 | 122 / 87 |
| 0.04 (median break-even) | 13 / 13 | 13 / 13 | 8 / 8 | 27 / 20 | 15 / 8 | 76 / 62 |

**No group closes at any pump-safe price.**

- **Group 1 is untouched below 0.04.** Biotite electrolysis gains 7,207 EMC on 44 of input; it would need about
  0.3 EMC/EU.
- **Some loops can't close at any price.** The primitive blast furnace steel loop uses no EU. Tiny-EU recipes
  (ULV macerator, packer, lathe) would need more than 2 EMC/EU.
- **The model re-run agrees.** It replays the whole value graph, so energy also raises other outputs. It closes 11 /
  17 / 30 / 102 of its 273 baseline exploits at 5e-5 / 4e-4 / 0.0016 / 0.04. Some prices open new ones: at 4e-4 the
  count gaining 100+ EMC goes from 217 to 225. The model over-counts lathes (80 rows; the mod splits those by share).

## 3. The pump check

At price *p*, a generator gains EU/s × *p* − fuel EMC/s by putting its EU into recipe outputs and banking them. The
worst generator at each price:

| EMC/EU | Worst generator | EMC/s | EMC per hour |
|---|---|---:|---:|
| 5e-5 (H = 100 h) | Large tungstensteel boiler, dried kelp | +3.9 | +14,000 |
| 4e-4 (H = 10 h) | same | +27.6 | +99,000 |
| 0.0016 (diesel) | same | +102 | +368,000 |
| 0.04 | same | +2,560 | +9.2 M |
| rising ×2, IV recipes (0.0256) fed with LV-priced EU | same | +1,638 | +5.9 M |

- **The derived price holds.** At p = min over generators of (fuel + EMC/H) ÷ EU, every generator's gain is at most
  its own EMC ÷ H. That is the time term, not fuel turned into EMC: no generator gains EMC above its fuel and time.
  With H = 100 h every generator stays under 5 EMC/s.
- **The other schemes fail.** The diesel price, any price that closes loops, and any schedule rising with tier all
  fail. A rising schedule fails by construction, because LV-made EU runs IV recipes.

## 4. Floors (#59 decision 3)

Without floors, at 5e-5, the late tiers collapse: IV 4.4, LuV 2.5, ZPM 1.2 and UV 2.5 Prestiges.

| Prestiges per tier | LV | MV | HV | EV | IV | LuV | ZPM | UV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Floors, 0 (model baseline) | 6.3 | 8.2 | 6.8 | 4.5 | 5.3 | 5.7 | 9.2 | 9.7 |
| Floors, 5e-5 | 6.3 | 8.2 | 6.8 | 4.5 | 5.3 | 5.7 | 9.2 | 9.8 |
| Floors, 0.0016 | 6.3 | 8.2 | 6.8 | 4.5 | 5.4 | 5.9 | 9.7 | 11.1 |
| No floors, 0 | 6.3 | 8.2 | 6.8 | 4.5 | 4.4 | 2.5 | 1.1 | 2.3 |
| No floors, 5e-5 | 6.3 | 8.2 | 6.8 | 4.5 | 4.4 | 2.5 | 1.2 | 2.5 |
| No floors, 0.0016 | 6.3 | 8.2 | 6.8 | 4.5 | 4.4 | 3.0 | 2.6 | 6.4 |
| No floors, rising ×2 | 6.3 | 8.2 | 6.8 | 4.5 | 4.6 | 7.8 | 20.5 | 107.8 |
| No floors, rising ×4 | 6.3 | 8.2 | 6.8 | 4.5 | 5.5 | 86.0 | 738.5 | 11,009 |

- **Fusion products.** A fusion recipe's energy per 144 mB of output (`eu_to_start` is paid once per start, so it
  isn't counted) is 0.4 M EU for indium up to 113 M EU for naquadria. At 5e-5 that adds 20–5,700 EMC per ingot,
  against floors of 32,768–196,608.
- **Non-fusion materials.** With energy counted and no floors, at 0.0016 tungsten is 2,243 (floor 131,072) and
  ruthenium 4,961 (floor 196,608).
- **Only a pumping schedule could replace the floors.** Rising ×2 brings LuV into range, but overshoots ZPM and UV.

**Energy can't replace or reduce the floors at a pump-safe price.**

## 5. Implementation sketch (if #25 makes EU expensive)

**Recipe energy, in `GtRecipeEmcMapper`.** For each GT recipe:

- **EU per run:**
  `EnergyStack in = recipe.getInputEUt(); long eu = in.voltage() * in.amperage() * recipe.duration;`. The GT 8.0 API
  is `GTRecipe.getInputEUt()` / `getOutputEUt()`, which return `EnergyStack(voltage, amperage)`.
- **Skip:** generator recipes (`getOutputEUt()` non-empty) and recipes with no consumed input. Leave out the fusion
  start energy (`recipe.data.getLong("eu_to_start")`).
- **Add the cost:** add `eu × price` of the existing 1-EMC fake node (`unit`) to the recipe's inputs before
  `OutputShares` splits them. Keep it as a `BigFraction`, because the cost is usually well under 1 EMC per run.

**The price, in mod config.** A common-config value `emc.euPrice` (EMC per EU; default 0 = off), optionally a per-tier
list read through `RecipeHelper.getRecipeEUtTier(recipe)`. The Pack sets it in
`pack/config/mcincremental_prestige-common.toml`. A pack-side smoke assertion should then check that
price ≤ the cheapest generator's cost from `eu_price.py`.

## Group 4 and energy

Group 4's decision (a) prices gases split off by chemistry at their recipe cost. Energy adds almost nothing to that
cost at a pump-safe price:

- **Methane electrolysis:** 600 EU, so 0.03 EMC at 5e-5.
- **Water electrolysis:** 45,000 EU for 2 buckets of H₂ and 1 of O₂, so 0.75 EMC per bucket at 5e-5 and 24 per bucket
  at the diesel price.
- **Gas collector:** 3,200 EU per 10 buckets of air, so 0.016 EMC per bucket at 5e-5, against the tier anchor of 64.
  Reaching 64 through energy would take 0.2 EMC/EU.

So the tier anchor for gas-collector output stays a policy value. The mapper skips recipes with no consumed input
anyway. Water electrolysis stays in #59's free-fluid list: water is free, so under decision (a) its H₂ and O₂ would
otherwise be worth about 1 EMC.

## Caveats

- **Boiler figures come from bytecode.** The steam rates and large-boiler fuel durations are untested in game, and the
  large-boiler bills are approximate.
- **Generators only above LV.** Simple generators above LV aren't modelled, since they are not more fuel-efficient.
  Raw oil and light oil are left out (no Fluid Drilling Rig).
- **The model sees energy only in its GT conversions.** `generate.py`'s other pins (recipe consistency, processing
  pins) don't, and the model differs from the game (273 vs 181 exploits at price 0). Hence the first-order table above,
  which uses the in-game values.

## Reproduce

From `docs/research/emc-pricing/`:

```sh
python3 eu_price.py > eu_price.txt                  # generators, derived price, pump check
python3 energy_sweep.py /tmp/sweep > energy_sweep.txt  # ~10 min; models, audits, Prestiges per scenario
EMC_EU_PRICE=5e-5 GEN_OUT=gen.json python3 generate.py && EMC_EU_PRICE=5e-5 python3 audit.py --model gen.json
```

- **`EMC_EU_PRICE`** is a number, or JSON `{tier: price}`. It is read by `emcmodel.py` and `audit.py`.
- **`EMC_EU_DUMP`** overrides the default `eu.txt.xz`.
- **`eu.txt.xz`** comes from `dump_eu.js`: a smoke-test server running the v0.3.0 Pack, set up the same way as
  `dump.js`.
