# EMC pricing (#55)

Generates the Pack's EMC values, `pack/config/ProjectE/custom_emc.json` and
`pack/kubejs/data/mcincremental_prestige/fluid_emc/fluids.json`, so that every obtainable item and fluid but water has
EMC. The method and its decisions are in `docs/pocs/poc-1.md` ("How EMC values are made").

## Files

| File | What |
|---|---|
| `generate.py` | Writes both files (`--write`); without it, prints the report only. |
| `emcmodel.py` | Offline replay of ProjectE's mapping and the Prestige mod's GT recipe mapper (#52), from a dump. |
| `hand_values.json` | The hand-set values (with reasons) and the fluids set by hand. Edit this, then re-run. |
| `rarity.py` → `rarity.json` | Rarity prices: material units per Run (all dimensions) and their EMC value. |
| `extract_ores.py` → `ore_counts.json` | Mean ore blocks per Run area per dimension, from the research dumps (`../emc-economy.md`, `../dimensions.md`). |
| `extract_yields.py` → `ore_yields.json` | What crushing and processing each ore yields, from a recipe dump. |
| `dump.js` | KubeJS dump (items, fluids, tags, recipes) for a smoke-test server. |
| `dump.txt.xz` | The dump the committed values were generated from (Pack with the values it generated running). |
| `game_caps.json` | Listed fluids capped at a cheaper route ProjectE found in the game; kept so re-runs are stable. |
| `projecte_defaults/` | ProjectE PE1.1.0's own default values (`data/projecte/pe_custom_conversions`, MIT). |
| `audit.py` | Lists GT recipes that still gain 100+ EMC, including those ProjectE's scan can't see. |

## Reproduce

```sh
python3 rarity.py > rarity.json   # from ore_counts.json and ore_yields.json
python3 generate.py --write       # from dump.txt.xz and projecte_defaults/: gives the committed files exactly
python3 audit.py                  # what still gains 100+ EMC
```

## Update after a Pack change

The model is checked against the game, so a new dump is needed whenever recipes or values change:

1. Copy `scripts/smoke-test.sh` and run it with `SMOKE_WORK_DIR` set and a hook, after the Pack is installed and
   before the server boots, that appends `dump.js` to the work dir's `kubejs/server_scripts/smoke_test.js` and calls
   `emcPricingDump(server)` first thing in its `runAssertions`.
2. Strip the log: `grep -oE '(EMCDUMP|FLUIDDUMP|TAGDUMP|RDUMP|EMC Exploit:).*' console.log | xz -9 > dump.txt.xz`.
3. `python3 generate.py --write`, `packwiz refresh` in `pack/`, and run the smoke test. Values settle within a run or
   two: the generator reads the game's values and exploit warnings from the dump (tiny dusts the game prices below 1
   EMC, fluids ProjectE found a cheaper route to), and the last dump should come from a server running the values it
   generated.
4. If recipes changed, also `python3 extract_yields.py <console.log> > ore_yields.json` and re-run `rarity.py`.
