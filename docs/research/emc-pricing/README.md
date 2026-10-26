# EMC pricing (#55, re-based in #59)

Generates the Pack's EMC values, `pack/config/ProjectE/custom_emc.json` and
`pack/kubejs/data/mcincremental_prestige/fluid_emc/fluids.json`, so that every obtainable item and fluid but water has
EMC, against the Prestige mod v0.3.0's GT recipe mapper (it splits each recipe's cost across its outputs). The method
and its decisions are in `docs/pocs/poc-1.md` ("How EMC values are made").

The balancing metric (owner decision, #59) is **Prestiges per tier: about 5-10 per tier**, counting the Runs spent
discovering the tier's materials. `prestiges_per_tier.py` reports it from a dump; its output is committed as
`prestiges_per_tier.txt`, and the audit's as `audit.txt`.

## Files

| File | What |
|---|---|
| `generate.py` | Writes both files (`--write`); without it, prints the report only. |
| `emcmodel.py` | Offline replay of ProjectE's mapping and the GT recipe mapper's first-output conversions (#52), from a dump. It steers the pins; the game (a dump) is what the reports read. |
| `hand_values.json` | Hand-set values (with reasons), the free fluids' anchor, the late-tier `floors`, tag pins, and `accepted_exploits` (outputs the smoke test exempts, each with its reason). Edit this, then re-run. |
| `rarity.py` → `rarity.json` | Rarity prices: material units per Run in the dimension that yields the most, and their EMC value. `EXPONENT` and `MAX_VALUE` are the dials. |
| `extract_ores.py` → `ore_counts.json` | Mean blocks per Run area per dimension (ores and every other block), from the research dumps (`../emc-economy.md`, `../dimensions.md`). End areas with too little land are left out. |
| `extract_yields.py` → `ore_yields.json` | What crushing and processing each ore yields (ore washer and chemical bath routes), and what crushing each rock yields, from a recipe dump. |
| `prestiges_per_tier.py` → `prestiges_per_tier.txt` | Prestiges per tier: kit cost, net EMC per Run by dimension, discovery Runs (a Monte Carlo over Candidate areas). |
| `audit.py` → `audit.txt` | GT recipes whose outputs are worth more than 1.1x their inputs at machine speed, including those ProjectE's scan can't see. |
| `dump.js` | KubeJS dump (items, fluids, tags, recipes with their duration and voltage tier) for a smoke-test server. |
| `dump.txt.xz` | The dump the committed values were generated from (Pack with the values it generated running). |
| `game_caps.json` | Generated: listed fluids and material units capped at a cheaper route ProjectE found in the game, and the metals whose dust and ingot the game split; kept so re-runs are stable. |
| `game_zero.json` | Generated: items a dump showed at 0 although the model values them; kept so re-runs are stable. |
| `projecte_defaults/` | ProjectE PE1.1.0's own default values (`data/projecte/pe_custom_conversions`, MIT). |

## Reproduce

```sh
python3 rarity.py > rarity.json                 # from ore_counts.json and ore_yields.json
python3 generate.py --write                      # from dump.txt.xz and projecte_defaults/: gives the committed files
python3 prestiges_per_tier.py > prestiges_per_tier.txt
python3 audit.py > audit.txt
```

`RARITY_EXPONENT`, `RARITY_MAX` (rarity.py) and `EMC_FLOORS` (a JSON `{material: floor}`, generate.py) override the
dials for sweeps; `generate.py --model`-style checks are `GEN_OUT=gen.json python3 generate.py` followed by
`prestiges_per_tier.py --model gen.json` or `audit.py --model gen.json`.

## Update after a Pack change

The model only steers the pins; the game is checked, so a new dump is needed whenever recipes or values change:

1. Copy `scripts/smoke-test.sh` and run it with `SMOKE_WORK_DIR` set and a hook, after the Pack is installed and
   before the server boots, that appends `dump.js` to the work dir's `kubejs/server_scripts/smoke_test.js` and calls
   `emcPricingDump(server)` first thing in its `runAssertions`.
2. Strip the log: `grep -oE '(EMCDUMP|FLUIDDUMP|TAGDUMP|RDUMP|EMC Exploit:).*' console.log | xz -9 > dump.txt.xz`.
3. `python3 generate.py --write`, `packwiz refresh` in `pack/`, and run the smoke test. Values settle within a few
   runs: the generator reads the game's values and exploit warnings from the dump (items the game floors to 0, metals
   whose dust and ingot it splits, routes cheaper than a listed fluid or a material's unit), and the last dump should
   come from a server running the values it generated.
4. If recipes changed, also `python3 extract_yields.py <console.log> > ore_yields.json` and re-run `rarity.py`; if the
   world generation changed, re-run the research dumps and `extract_ores.py`.
5. Re-run `prestiges_per_tier.py` and `audit.py` and commit their output.
