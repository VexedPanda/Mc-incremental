# Mc-incremental

A Minecraft modpack played as an incremental game. Each **Run** is confined to a tiny, resource-starved patch of an ordinary world (a 3×3-chunk Run area). Progress through GregTech until the area runs dry, then **Prestige**. Everything you built is refunded as EMC, and you start again in a fresh area, keeping the world's Knowledge (every resource it has learned) and its EMC balance.

The current build is **PoC 1**, the first test of whether the loop is fun. It runs on Minecraft 1.21.1 with NeoForge 21.1.264.

## The loop

1. Start in a fresh Run area with a Transmutation Tablet. The world border keeps you inside the area.
2. Mine, build and climb the GregTech tiers with what the area holds. There is no free resource generation beyond low-value renewables.
3. Learn resources through ProjectE. Learned resources can be recreated from the shared EMC balance, and EMC barrels move items and fluids in and out of it automatically.
4. Prestige when you're stuck. The Prestige sweep converts every block, machine, inventory, tank and dropped item you added into EMC, then moves everyone to a new, never-visited area.

The design is still evolving: see [`docs/pocs/poc-1.md`](docs/pocs/poc-1.md), the decisions in [`docs/adr/`](docs/adr/), and the vocabulary in [`GLOSSARY.md`](GLOSSARY.md). Open design questions are GitHub issues labelled `needs-triage`.

## Mods

| Mod | Role |
|---|---|
| [GregTech CEu](https://github.com/GregTechCEu/GregTech-Modern) 8.0 snapshot (pinned, mirrored in this repo's releases) | Content mod: the progression within a Run |
| [ProjectE](https://www.curseforge.com/minecraft/mc-mods/projecte) | EMC and Knowledge, carried across Prestiges |
| [Mc-incremental Prestige](https://github.com/VexedPanda/mc-incremental-prestige) | Run areas, Prestige, Prestige sweep, EMC barrel |
| KubeJS (+ Rhino) | Recipe and EMC changes in the pack |
| EMI, Jade, Better Advanced Tooltips | Quality of life |

## Playing

Each pack PR's CI builds a Modrinth pack (`.mrpack`), available as a workflow artifact. Import it into Prism Launcher, the Modrinth App or any launcher that reads `.mrpack`.

## Repository layout

| Path | What |
|---|---|
| `pack/` | The [packwiz](https://packwiz.infra.link/) pack. Only this ships to players |
| `pack/kubejs/` | Recipe removals, EMC data and the smoke-test assertions |
| `pack/config/` | Mod configs (GregTech, ProjectE EMC pins) |
| `scripts/smoke-test.sh` | Boots the pack on a headless NeoForge server and fails unless the KubeJS assertions pass |
| `scripts/check-client-defaults.sh` | Checks the client install's default options |
| `docs/` | PoC specs, ADRs, research |
| `.github/workflows/` | Pack check and `.mrpack` export (PRs), smoke test (nightly and manual), GregTech mirror (manual) |

## Developing

```sh
cd pack
packwiz refresh                 # after any change under pack/
cd ..
scripts/smoke-test.sh           # about a minute; needs java 21, curl, python3, flock
```

Add a smoke assertion in `pack/kubejs/server_scripts/smoke_test.js` for each configuration change. More detail for contributors (and agents) is in [`CLAUDE.md`](CLAUDE.md). Work is tracked in GitHub Issues.

## License

Apache-2.0.
