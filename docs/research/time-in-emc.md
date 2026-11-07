# Time in EMC (#64)

The owner decided on #64 that time is a real cost the player pays. Every GT recipe's EMC value is therefore:

- its material inputs;
- plus its EU × the EU price;
- plus its duration × R, where R is the EMC per machine-second at the recipe's tier.

EU is valued like any recipe:

- **EU price at a tier:** the minimum, over the generators available by that tier, of (fuel EMC + generator time × R) ÷ EU made.
- **Free generators:** solar fuel is 0, so solar EU costs only its time.
- **Exploits:** a loop that gains no more than its machine's time cost is paying for that time. Only a loop that gains more than R per machine-second is an exploit.

This note compares five schedules for R. It is research only: no value in the Pack or the Prestige mod changes. It
replaces the recommendation in `energy-in-emc.md`, which assumed time costs nothing. The scripts and outputs are in
`emc-pricing/` (see "Reproduce").

## Recommendation

**I recommend R = LV 4 ×2 per tier (ULV 2, LV 4, MV 8, HV 16, EV 32, IV 64, LuV 128, ZPM 256, UV 512 EMC/s).**
Derive the EU price per tier from the cheapest generator, and keep #59's floors.

- **×2 per tier is the slowest overclock-safe rise.** GT's normal overclock runs a recipe twice as fast per tier
  above its own. A recipe valued at its own tier and duration then earns 2^k × R(t) per second in a machine k tiers
  up. That stays at or below that machine's R only if R at least doubles per tier.
  - **Flat R fails this check:** at flat 4, an LV recipe in a UV machine earns 128 × R (512 EMC/s).
  - **×4 schedules pass it with room to spare.** They also pass perfect overclocks (EBF coil bonus), where ×2
    doesn't. Those are rare enough to accept.
- **×2 keeps time income small next to a Run.** A base of 10 machines plus their generators needs 17–45 hours of
  banked running to earn one Run's EMC through EV, 9 h at LuV, and still 1.2 h at UV.
  - **Under ×4 time takes over the economy.** From LV 4 ×4, a LuV base earns a Run's worth in 0.4 h and a UV base
    earns 2.9 billion EMC per hour.
- **×2 keeps the Prestige balance where it is.** With floors it gives 5.4 / 5.8 / 9.5 / 10.3 Prestiges for IV to
  UV, close to today's 5.2 / 5.6 / 8.1 / 9.2.
- **Time can't replace the floors** under any schedule (section 3).
- **What ×2 closes:** 58 of #63's 181 loops, and 35 of the 134 gaining 100+ EMC per run. The rest are loops
  whose outputs are pinned (rarity prices, hand-set fuels, tier-priced gases). Time can't close them; #63's pricing
  decisions still have to.
- **The step-down pump is bounded and small.** A low-tier recipe run on cheap late-game EU earns at most 1 × R
  extra under ×2 (+4 EMC/s on an LV machine). If the owner wants zero, price all EU at the cheapest generator anywhere
  (section 5).

**Before implementing,** fix one pump that appears under every schedule. Crafting-table recipes that use a GT tool
are instant, and ProjectE doesn't map them. With time counted, about 1,000 of them make items worth more than their
inputs (section 5). The mapper has to map them, with the tool not consumed, so that the cheaper instant route sets the
value.

## 1. EU price per tier, and the generator that sets it

The generators are listed in `eu_price.py`'s `timed_generators`:

- **Single-block generators:** LV, MV and HV combustion generators and gas turbines.
- **Large generators:** the large and extreme combustion engines, the large gas turbine, and the large plasma
  turbine (`2 × V[tier]` EU/t at 100% rotor, from GT 8.0's `LargeTurbineMachine`). The plasma turbine needs LuV
  fusion for its fuel.
- **Boilers:** small and large boilers, with either LV steam turbines or large steam turbines.
- **Solar:** ULV and LV solar panel covers, at 50% daylight.

Each machine in a setup pays its own time at R of its tier. A large boiler, for example, also pays for its turbines.
Pass 2 re-derives the prices from the time-inclusive model values. Every price moved by less than 1%, so pass 1 is
used below.

| Tier | LV 4 ×4 | LV 4 ×2 | LV 1 ×4 | flat 4 | Prestige-derived |
|---|---|---|---|---|---|
| LV | 6.3e-3 (LV gas turbine) | 6.3e-3 (LV gas turbine) | 1.6e-3 (LV gas turbine) | 6.3e-3 (LV gas turbine) | 1.6e-3 (LV gas turbine) |
| MV | 6.3e-3 (LV gas turbine) | 3.2e-3 (MV gas turbine) | 1.6e-3 (LV gas turbine) | 1.6e-3 (MV gas turbine) | 1.6e-3 (LV gas turbine) |
| HV | 3.7e-3 (large bronze boiler + large steam turbines) | 1.2e-3 (large steel boiler + LST) | 9.3e-4 (large bronze boiler + LST) | 4.3e-4 (large steel boiler + LST) | 9.3e-4 (large bronze boiler + LST) |
| EV, IV | 1.7e-3 (large gas turbine) | 2.8e-4 (large gas turbine) | 4.8e-4 (large gas turbine) | 1.1e-4 (large gas turbine) | 4.8e-4 (large gas turbine) |
| LuV–UV | 1.6e-3 (large plasma turbine) | 9.8e-5 (large plasma turbine) | 3.9e-4 (large plasma turbine) | 6.1e-6 (large plasma turbine) | 4.8e-4 (large gas turbine) |

Values are EMC per EU. The gas turbines burn butadiene. The boilers burn dried kelp blocks. The plasma turbine burns
argon plasma (iron plasma in pass 2).

- **Time sets the price, not fuel.** Solar never wins: a panel cover's EU per machine-second is too low.
- **Big generators make EU cheap.** At every tier, the cheapest generator is the one that makes the most EU per
  machine-second. So with R flat, EU falls about 1,000× from LV to LuV, as the owner expects of endgame GT.

## 2. Loops

**First order.** Each of the 181 in-game exploits in `audit.txt` pays its EU and its time, with the in-game values
otherwise unchanged. A loop is still open if its outputs are worth more than 1.1 × (inputs + EU + time) and it gains
10+ EMC per run and 5+ EMC/s above its time.

| Schedule | Open (100+/run) | G1 cheap inputs | G2 ore chains | G3 refinery | G4 gas chemistry | G5 other | Worst gain above time |
|---|---:|---:|---:|---:|---:|---:|---|
| none | 181 (134) | 19 | 36 | 35 | 61 | 30 | gasoline 13,500 EMC/s |
| LV 4 ×4 | 97 (81) | 14 | 18 | 13 | 36 | 16 | gasoline 13,405 EMC/s |
| **LV 4 ×2** | **123 (99)** | 16 | 25 | 23 | 43 | 16 | gasoline 13,476 EMC/s |
| LV 1 ×4 | 141 (102) | 18 | 25 | 28 | 48 | 22 | gasoline 13,479 EMC/s |
| flat 4 | 133 (107) | 17 | 29 | 26 | 44 | 17 | gasoline 13,496 EMC/s |
| Prestige-derived | 141 (102) | 18 | 25 | 28 | 48 | 22 | gasoline 13,479 EMC/s |

**No group closes completely.** The loops still open under LV 4 ×2, with the worst gain above time in each group:

- **G1 cheap inputs:** potash electrolysis 988 EMC/s, lithium chloride 878, andesite centrifuging 742, biotite 316.
- **G2 ore chains:** Prussian blue 1,938, phosphoric acid from apatite 1,378.
- **G3 refinery:** the gasoline and diesel recipes up to 13,476.
- **G4 gas chemistry:** DTPA 1,039, isoprene 325.
- **G5 other:** dark ash tiny dust unpacking 1,696, epoxy plate recycling about 960, the olivine lathe 677.

All of these make a pinned output (a rarity price, a hand-set fuel, a tier-priced gas). Their gain is in the price
of the output, not a missing cost, so they stay #63's pricing decisions.

**The model re-run.** `generate.py` replays the whole value graph with time and EU counted, then `audit.py --model`
runs on the result. The model has 273 baseline exploits; the schedules leave 242 (×4), 262 (×2), 260 (LV 1 ×4) and
269 (flat). Its worst row becomes `desulfurize_heavy_fuel`, a hand-set fuel: heavy fuel's sulfuric inputs rise with
time, but its output doesn't. See `time_sweep.txt`.

## 3. Prestiges per tier, and the floors

Kit cost goes up because every recipe in a kit's tree now carries its time. The EMC per Run doesn't change, because a
Run's EMC is raw blocks. Each cell is Prestiges, with the kit cost in millions of EMC:

| Schedule | Floors | IV | LuV | ZPM | UV |
|---|---|---:|---:|---:|---:|
| none | full | 5.3 (63) | 5.7 (233) | 9.2 (600) | 9.7 (634) |
| none | none | 4.4 (3) | 2.5 (24) | 1.1 (72) | 2.3 (148) |
| LV 4 ×4 | full / half / none | 5.4 / 4.9 / 4.5 | 6.7 / 5.4 / 4.1 | 12.4 / 9.1 / 5.9 | 19.4 / 15.7 / 14.7 |
| **LV 4 ×2** | full / half / none | 5.4 / 4.9 / 4.4 | 5.8 / 4.2 / 2.8 | 9.5 / 5.4 / 1.7 | 10.3 / 6.2 / 4.0 |
| LV 1 ×4 | full / half / none | 5.4 / 4.9 / 4.5 | 5.9 / 4.5 / 3.1 | 10.0 / 6.4 / 3.1 | 12.1 / 8.7 / 7.7 |
| flat 4 | full / half / none | 5.4 / 4.9 / 4.4 | 5.7 / 4.1 / 2.5 | 9.3 / 5.2 / 1.2 | 9.9 / 5.8 / 2.5 |
| Prestige-derived | full / half / none | 5.4 / 4.9 / 4.5 | 6.4 / 5.2 / 3.9 | 11.4 / 8.2 / 5.1 | 14.6 / 11.2 / 10.4 |

LV to EV don't move (6.3–6.4, 8.2, 6.8, 4.5): those tiers' kits are cheap and their Prestiges come from discovery
Runs.

**The Prestige-derived schedule.** It follows LV 1 ×4 up to EV, then sets IV 2,048, LuV 4,096, ZPM 8,192 and
UV 16,384, still rising ×2 so that it passes the overclock check. Higher IV rates were tried, from 2,048 to 16,384
(`time_sweep.py` and the tuning notes in its header):

- **They overshoot UV before LuV reaches 5.** UV's kit is made of ZPM and LuV parts, so it grows about twice as fast
  as ZPM's.
- **IV stays at 4.5 at any rate.** Its kit is mostly lower-tier time: GT machines are crafted in a crafting table.

**Time can't replace the floors.**

- **The extra kit cost is earned back fast.** Every EMC that time adds to a kit is EMC that the same machines earn
  back by running. The last column of the base tables in `time_sweep.txt` is the hours a 10-machine base needs to
  earn back what time adds to its tier's kit: under 1 h for every rising schedule except ×2 (about 2 h at
  LuV–UV).
- **Floors are a different kind of cost.** A floor prices a material a Run can't yield. Time prices something the
  player already has more of each tier.
- **Raising R to stand in for the floors would make machine time pay for the kit.** Running the base would replace
  mining Runs, which undoes the Prestige metric.
- **Keep the floors.** Under ×2 they can stay as they are. Under ×4 they would need lowering at ZPM and UV, which
  overshoot (12.4 and 19.4).

## 4. What a base earns per hour

A base here is 10 machines at the tier, each at 1 A of V[tier], plus the price-setting generators that power them.
All of it runs for the whole hour, and every output is banked. That is an upper bound. The figures are time income
only, in EMC per hour; materials, fuel and EU are paid for. "Hours per Run" compares it with net EMC per Run (6.6 M at
LV, 9.9 M at MV, 33 M at HV, 65 M from EV).

| Tier | LV 4 ×4: EMC/h (hours per Run) | LV 4 ×2 | LV 1 ×4 | flat 4 | Prestige-derived |
|---|---:|---:|---:|---:|---:|
| LV | 288 k (23) | 288 k (23) | 72 k (92) | 288 k (23) | 72 k (92) |
| MV | 1.15 M (8.6) | 576 k (17) | 288 k (34) | 288 k (34) | 288 k (34) |
| HV | 3.6 M (9.0) | 1.0 M (32) | 0.9 M (36) | 298 k (110) | 0.9 M (36) |
| EV | 11.5 M (5.7) | 1.4 M (45) | 2.9 M (23) | 180 k (362) | 2.9 M (23) |
| IV | 46 M (1.4) | 3.5 M (19) | 11.5 M (5.7) | 288 k (226) | 76 M (0.9) |
| LuV | 184 M (0.4) | 6.9 M (9.4) | 46 M (1.4) | 288 k (226) | 157 M (0.4) |
| ZPM | 737 M (0.1) | 18 M (3.5) | 184 M (0.4) | 720 k (91) | 332 M (0.2) |
| UV | 2.9 B (0.02) | 55 M (1.2) | 737 M (0.1) | 2.4 M (27) | 737 M (0.1) |

- **Generators earn too.** A generator's EU sells for its fuel plus its time, so banking the outputs also pays the
  generators' time.
- **The UV figures under ×2 are mostly generators.** At UV most of ×2's income (37 M of 55 M) is the 160 plasma
  turbines that 10 UV machines need.

## 5. Pumps

**The step-down pump.** A tier's recipe is valued at that tier's EU price, but it can run on the cheapest EU anywhere
(late-game EU stepped down through transformers). The table gives the extra EMC/s per machine at 1 A of V[tier], as
a share of that tier's R:

| Tier | LV 4 ×4 | LV 4 ×2 | LV 1 ×4 | flat 4 | Prestige-derived |
|---|---:|---:|---:|---:|---:|
| LV | +3.1 (76%) | +4.0 (100%) | +0.8 (81%) | +4.1 (101%) | +0.8 (75%) |
| MV | +12 (76%) | +8.0 (100%) | +3.2 (81%) | +4.2 (105%) | +3.0 (75%) |
| HV | +21 (33%) | +12 (73%) | +5.5 (34%) | +4.3 (108%) | +4.6 (29%) |
| EV | +3.6 (1%) | +7.6 (24%) | +3.6 (6%) | +4.4 (109%) | 0 |
| IV | +14 (1%) | +30 (48%) | +14 (6%) | +17 (436%) | 0 |

- **Every rising schedule stays at or below R.** The generator already earns its own time, so the machine earns at
  most 2 × R, and the extra is a few EMC/s.
- **Flat R breaks it at IV, with 4.4 × R.** Its EU price falls about 1,000×, but R doesn't.
- **One flat EU price closes the pump in every schedule.** That price is the cheapest anywhere. The cost is that a
  low-tier player's own EU is then worth less than it cost, and their processing earns R minus that loss. Under ×2 at
  LV, that is about 0.

**Overclocking.** A recipe run in a higher-tier machine earns its time faster than its own tier's rate. The worst
case per schedule, as a multiple of the faster machine's R:

| Schedule | Normal overclock | Perfect overclock |
|---|---|---|
| LV 4 ×4 | 0.5 × R | 1.0 × R |
| LV 4 ×2 | 1.0 × R | 128 × R |
| LV 1 ×4 | 0.5 × R | 1.0 × R |
| flat 4 | **128 × R** (LV recipe in a UV machine, 512 EMC/s) | 16,384 × R |
| Prestige-derived | 1.0 × R | 8 × R |

Normal overclocking runs a recipe 2× as fast per tier. Perfect overclocking runs it 4× as fast per tier; the EBF's
coil bonus does this.

The same applies to **parallel recipes** (GCyM large machines and parallel hatches, not modelled). A multiblock that
runs N recipes at once earns N × R. Either accept that as the payoff of an expensive multiblock, or treat each
parallel as one machine.

**Generators.** No generator sells its EU above its fuel plus time at its own tier, because the price is the minimum
over generators. The only way a generator's EU earns more is through the step-down pump above.

**Instant crafting routes (new under every schedule).** ProjectE doesn't map crafting-table recipes that use a GT
tool (`emcmodel.py`, game mode), and those are instant.

- **How many:** 976 to 1,066 of them, depending on the schedule, make items worth more than their non-tool inputs.
  Without time counted, 63 do.
- **How much:** the worst under ×2 is the huge naquadah pipe, at +8,435 EMC per craft (+39,795 under LV 4 ×4).
- **The fix is in the mapper.** Map these recipes too, with the tool not consumed, so that the instant route caps the
  value. Hand crafting then carries no time, which matches the owner's "machine-second".

## 6. Mapper sketch (alongside EU, in `GtRecipeEmcMapper`)

For each GT recipe with a consumed input, the steps are below. Generator recipes are skipped, as for EU.

- **Find the tier:** `int tier = RecipeHelper.getRecipeEUtTier(recipe)`. A recipe with no EU is ULV.
- **Find the duration:** `recipe.duration` ticks, the listed duration, with no overclock or parallel.
- **Add both costs to the inputs, before `OutputShares` splits them:**
  - `eu × euPrice[tier] + duration / 20 × timeRate[tier]`;
  - as a `BigFraction` of the existing 1-EMC fake node (`unit`).

Two values go in the mod's common config, both off by default. The Pack sets them in
`pack/config/mcincremental_prestige-common.toml`:

- **`emc.timeRate`:** a per-tier list of EMC per machine-second.
- **`emc.euPrice`:** a per-tier list. The Pack sets it from `eu_price.py --rate`, so it is derived, not tuned.

Add pack-side smoke assertions for these:

- `timeRate[t+1] ≥ 2 × timeRate[t]` (the overclock check);
- every `euPrice` ≥ the cheapest generator's cost at that rate.

Also map crafting recipes that use GT tools (section 5). In `emcmodel.py` this is the game mode's `uses a tool`
skip.

## Caveats

- **Generator data is mostly from bytecode or estimated.**
  - The large turbine outputs (2 × V[tier] at a 100% rotor) and their tiers come from GT 8.0's bytecode.
  - The large combustion engines are taken without the oxygen boost.
  - Single-block generators above LV are assumed to burn as efficiently as LV ones.
  - Better rotors make EU cheaper still.
- **The recipe tier is the dump's `t`.** It matches the recipe's EU/t voltage tier for every recipe that uses EU.
  The 73 recipes with no EU (primitive blast furnace, coke oven, steam) are charged at ULV, or at their listed tier.
- **The base figures are upper bounds:** full uptime, 1 A per machine, every output banked.
- **The groups are approximate.** #63's groups are assigned from recipe ids (`energy_sweep.GROUPS`).

## Reproduce

From `docs/research/emc-pricing/`:

```sh
python3 time_sweep.py /tmp/time > time_sweep.txt   # ~5 min: EU price, first-order loops, model + audit + Prestiges
python3 eu_price.py --rate '{"ULV": 2, "LV": 4, "MV": 8, "HV": 16, "EV": 32, "IV": 64, "LuV": 128, "ZPM": 256, "UV": 512}'
EMC_TIME_RATE='{"ULV": 2, "LV": 4, ...}' EMC_EU_PRICE='{"ULV": 0.00634, ...}' GEN_OUT=gen.json python3 generate.py
EMC_TIME_RATE=... EMC_EU_PRICE=... python3 audit.py --model gen.json
```

- **`EMC_TIME_RATE`** is a number (flat R) or a JSON `{tier: R}`. A tier that is left out takes the R of the
  next lower listed tier. `emcmodel.py` and `audit.py` read it.
- **When it is unset,** every committed output is unchanged.
