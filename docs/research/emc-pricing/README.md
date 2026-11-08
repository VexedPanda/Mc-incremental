# EMC pricing (#55, re-based in #59, #68 and #72)

Generates the Pack's EMC values, `pack/config/ProjectE/custom_emc.json` and
`pack/kubejs/data/mcincremental_prestige/fluid_emc/fluids.json`, so that every obtainable item and fluid but water has
EMC, against the Prestige mod v0.5.0's GT recipe mapper (it splits each recipe's cost across its outputs, counts each
recipe's EU and machine time at rates built into the mod, #71, and derives and publishes every unlisted fluid). The
method and its decisions are in `docs/pocs/poc-1.md` ("How EMC values are made").

**The rule (owner decision on #72): pin only what no recipe can make from cheaper things, and let recipes set
everything else.** Pinned: raw materials (ore products, mob drops and other natural items no recipe creates) at their
rarity price, the late-tier floors, ProjectE's vanilla defaults (and the overrides where a recipe undercuts one: blaze
rod, nether star), the explicit fluid values (water, lava, steam, milk, the free fluids per tier) and the 0-EMC
Transmutation Tablet; plus the plumbing ProjectE needs to see anything at all (ore blocks and processing forms at
their yield, filled buckets, what the game leaves at 0 from valued inputs, values below 1 EMC). ProjectE takes the
cheapest route by itself, so nothing is capped: #63's R1 ceilings, `game_caps.json` and #41's hand-set GT fuels are
gone, and so are the hand pins a recipe derives (steel, wrought iron, GT cobblestone forms, dark concrete, magnesite
and magnesia).

The balancing metric (owner decision, #59) is **Prestiges per tier: about 5-10 per tier**, counting the Runs spent
discovering the tier's materials. `prestiges_per_tier.py` reports it from a dump; its output is committed as
`prestiges_per_tier.txt`, and the audit's as `audit.txt`.

## Files

| File | What |
|---|---|
| `generate.py` | Writes both files (`--write`); without it, prints the report only. |
| `emcmodel.py` | Offline replay of ProjectE's mapping and the GT recipe mapper's first-output conversions (#52), from a dump. It steers the pins; the game (a dump) is what the reports read. |
| `hand_values.json` | Hand-set values (with reasons): natural items no recipe makes, ProjectE defaults and the overrides they need, the explicit fluids, the late-tier `floors`, tag pins, and `accepted_exploits` (outputs the smoke test exempts, each with its reason). Edit this, then re-run. |
| `rarity.py` → `rarity.json` | Rarity prices: material units per Run in the dimension that yields the most, and their EMC value. `EXPONENT` and `MAX_VALUE` are the dials. |
| `extract_ores.py` → `ore_counts.json` | Mean blocks per Run area per dimension (ores and every other block), from the research dumps (`../emc-economy.md`, `../dimensions.md`). End areas with too little land are left out. |
| `extract_yields.py` → `ore_yields.json` | What crushing and processing each ore yields (ore washer and chemical bath routes), and what crushing each rock yields, from a recipe dump. |
| `prestiges_per_tier.py` → `prestiges_per_tier.txt` | Prestiges per tier: kit cost, net EMC per Run by dimension, discovery Runs (a Monte Carlo over Candidate areas). |
| `audit.py` → `audit.txt` | GT recipes whose outputs are worth more than 1.1x their inputs at machine speed, including those ProjectE's scan can't see. |
| `dump.js` | KubeJS dump (items, fluids, tags, recipes with their duration and voltage tier) for a smoke-test server. |
| `dump.txt.xz` | The dump the committed values were generated from (Pack with the values it generated running). |
| `dump_eu.js` | KubeJS dump of every GT recipe's EU (input and output EU/t, amperage, duration, fusion start energy) for the energy-in-EMC research (#64, `../energy-in-emc.md`). |
| `eu.txt.xz` | Its output, from a smoke-test server running the v0.5.0 Pack (#72; take it with the dump, below). |
| `eu_price.py` → `eu_price.txt` | EU price from generation cost (fuel plus generator EMC amortised over H hours), cheapest per tier, and the pump check (#64). |
| `energy_sweep.py` → `energy_sweep.txt` | Audit and Prestiges per tier at several EU prices, with and without floors (#64). `EMC_EU_PRICE` (EMC per EU, or JSON per tier) overrides the mod's EU price in `emcmodel.py` and `audit.py` (`0`: off). Research output, not re-run since #68. |
| `time_sweep.py` → `time_sweep.txt` | Time in EMC (#64, `../time-in-emc.md`): per schedule of R (EMC per machine-second), the EU price per tier from the cheapest generator (`eu_price.py --rate`), the in-game loops left, the model's audit and Prestiges per tier with full, half and no floors, base earnings per hour, and pump checks. `EMC_TIME_RATE` (a number, or JSON per tier) overrides the mod's time rate in `emcmodel.py` and `audit.py` (`0`: off). Research output, not re-run since #68. |
| `game_zero.json` | Generated: items and fluids a dump showed at 0 although a recipe makes them from inputs the game valued (a recipe ProjectE can't map, such as a smithing upgrade or an output with data components; a share split that gives a byproduct nothing; a tiny dust floored to 0), pinned at the model's value; kept so re-runs are stable. |
| `projecte_defaults/` | ProjectE PE1.1.0's own default values (`data/projecte/pe_custom_conversions`, MIT). |

## Reproduce

```sh
python3 rarity.py > rarity.json                 # from ore_counts.json and ore_yields.json
python3 generate.py --write                      # from dump.txt.xz and projecte_defaults/: gives the committed files
python3 prestiges_per_tier.py > prestiges_per_tier.txt
python3 audit.py > audit.txt
```

**Time and EU (#68, #71).** Since v0.5.0 the rates are built into the Prestige mod (4 EMC per machine-second at LV,
doubling every tier; the EU price per tier from `eu_price.py`), with no config. `emcmodel.py` mirrors them
(`BUILTIN_TIME_RATE`, `BUILTIN_EU_PRICE`), so every committed output counts them as the game does; `EMC_TIME_RATE` and
`EMC_EU_PRICE` (a number, or JSON per tier; `0` turns it off) override them for sweeps. The model maps neither GT tool
crafts nor the mapper's share split (it gives a recipe's whole cost to its first output), so `generate.py` only keeps
its values for what the game can't derive (step 4 of its docstring) and `audit.py --model` overstates loops; the in-game
`audit.txt` is the reference.

`RARITY_EXPONENT`, `RARITY_MAX` (rarity.py) and `EMC_FLOORS` (a JSON `{material: floor}`, generate.py) override the
dials for sweeps; `generate.py --model`-style checks are `GEN_OUT=gen.json python3 generate.py` followed by
`prestiges_per_tier.py --model gen.json` or `audit.py --model gen.json`.

## Update after a Pack change

The model only steers the pins; the game is checked, so a new dump is needed whenever recipes or values change:

1. Copy `scripts/smoke-test.sh` and run it with `SMOKE_WORK_DIR` set and a hook, after the Pack is installed and
   before the server boots, that appends `dump.js` and `dump_eu.js` to the work dir's
   `kubejs/server_scripts/smoke_test.js` and calls `emcPricingDump(server)` and `emcEuDump(server)` first thing in its
   `runAssertions`.
2. Strip the log: `grep -oE '(EMCDUMP|FLUIDDUMP|TAGDUMP|RDUMP|EMC Exploit:).*' console.log | xz -9 > dump.txt.xz` and
   `grep -oE 'EUDUMP.*' console.log | xz -9 > eu.txt.xz`.
3. `python3 generate.py --write`, `packwiz refresh` in `pack/`, and run the smoke test. Values settle within a few
   runs: the generator reads from the dump what the game leaves at 0 although its inputs have values (one layer per
   run: what is 0 only because an input was is left to the next) and what the game derives for each unlisted fluid (its
   bucket's pin), and the last dump should come from a server running the values it generated. Filled buckets lag one
   run behind the fluids they hold, so the smoke test's bucket check passes once the fluids stop moving.
4. If recipes changed, also `python3 extract_yields.py <console.log> > ore_yields.json` and re-run `rarity.py`; if the
   world generation changed, re-run the research dumps and `extract_ores.py`.
5. Re-run `prestiges_per_tier.py` and `audit.py` and commit their output.
