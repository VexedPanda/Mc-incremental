# Mc-incremental

A Minecraft modpack played as an incremental game. Each **Run** is confined to a tiny, resource-starved patch of an ordinary world (a 3×3-chunk Run area). Progress through GregTech until the area runs dry, then **Prestige**. Everything you built is refunded as EMC, and you start again in a fresh area, keeping the world's Knowledge (every resource it has learned) and its EMC balance.

The current build is **PoC 1**, the first test of whether the loop is fun. It runs on Minecraft 1.21.1 with NeoForge 21.1.264.

## The loop

1. Start in a fresh Run area with a Transmutation Tablet. The world border keeps you inside the area.
2. Mine, build and climb the GregTech tiers with what the area holds. There is no free resource generation beyond low-value renewables.
3. Learn resources through ProjectE. Learned resources can be recreated from the shared EMC balance, and EMC intakes move items and fluids into it automatically and EMC barrels hand them back out.
4. Prestige when you're stuck. The Prestige sweep converts every block, machine, inventory, tank and dropped item you added into EMC, then moves everyone to a new, never-visited area.

The design is still evolving: see [`docs/pocs/poc-1.md`](docs/pocs/poc-1.md), the decisions in [`docs/adr/`](docs/adr/), and the vocabulary in [`GLOSSARY.md`](GLOSSARY.md). Open design questions are GitHub issues labelled `needs-triage`.

## Mods

| Mod | Role |
|---|---|
| [GregTech CEu](https://github.com/GregTechCEu/GregTech-Modern) 8.0 snapshot (pinned, mirrored in this repo's releases) | Content mod: the progression within a Run |
| [ProjectE](https://www.curseforge.com/minecraft/mc-mods/projecte) | EMC and Knowledge, carried across Prestiges |
| [Mc-incremental Prestige](https://github.com/VexedPanda/mc-incremental-prestige) | Run areas, Prestige, Prestige sweep, EMC barrel, EMC intake |
| KubeJS (+ Rhino) | Recipe and EMC changes in the pack |
| EMI, Jade, Better Advanced Tooltips | Quality of life |

## Playing and testing

You need Java 21 and a launcher that can run NeoForge, such as [Prism Launcher](https://prismlauncher.org/) (recommended), the Modrinth App or CurseForge. Allocate at least 6 GB of RAM: GregTech is heavy.

### Option A: auto-updating Prism instance (best for testing a branch)

Every launch pulls the latest pack from a branch using [packwiz-installer](https://packwiz.infra.link/tutorials/installing/packwiz-installer/).

1. In Prism, choose **Add Instance**, then **Custom**: Minecraft **1.21.1**, loader **NeoForge 21.1.264**.
2. Download [`packwiz-installer-bootstrap.jar`](https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest) into the instance's `minecraft` folder (**Edit → Folder**).
3. Under **Edit → Settings → Custom commands**, tick the box and set the **Pre-launch command**. Replace `main` with the branch you want to test, for example `integration/poc1-pack`:
   ```
   "$INST_JAVA" -jar packwiz-installer-bootstrap.jar https://raw.githubusercontent.com/VexedPanda/Mc-incremental/main/pack/pack.toml
   ```
4. Under **Settings → Java**, set the maximum memory to at least 6144 MB.
5. Launch. The first launch downloads every mod. Later launches only fetch what changed.

### Option B: a `.mrpack` file

1. Get the file in either of these ways:
   - Open a pack PR, then **Checks → pack → Summary → Artifacts → `mrpack`**. GitHub serves it zipped, so unzip it to get `mc-incremental.mrpack`.
   - Build it locally: `cd pack && packwiz modrinth export`.
2. Import it. In Prism that's **Add Instance → Import** and choose the file. In the Modrinth App it's **+ → Import from file**.
3. Set the memory to at least 6 GB and launch.

This doesn't update itself: re-import to get a newer pack.

### Dedicated server

```sh
mkdir server && cd server
java -jar neoforge-21.1.264-installer.jar --installServer   # from maven.neoforged.net
curl -LO https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest/download/packwiz-installer-bootstrap.jar
java -jar packwiz-installer-bootstrap.jar -g -s server https://raw.githubusercontent.com/VexedPanda/Mc-incremental/main/pack/pack.toml
echo eula=true > eula.txt && ./run.sh nogui
```

The pack ships `server.properties` with view and simulation distance set to 2.

### What to try

- **New world:** you spawn inside a Run area of 3×3 chunks bounded by the world border, holding a Transmutation Tablet. Use **Default** world generation, not superflat.
- **EMC:** put items into the tablet to learn them and add EMC to the world balance, then take them back out. Craft an **EMC barrel** (a barrel plus redstone) and right-click it with a learned item, or with a bucket of a learned fluid, to choose what it hands out. Pull from it; it only hands out. To bank items and fluids automatically, craft an **EMC intake** (a hopper plus redstone) and pipe anything into it, or right-click it with a stack or a filled bucket: everything with an EMC value is converted into the world balance and learned (water and other worthless things are refused and stay in the pipe).
- **Prestige:** run `/prestige` (with cheats or op), or craft the **Prestige** item (one dirt, sand or cobblestone), use it once, then sneak-use it within 5 s to confirm. Everything you placed, along with machine and chest contents, is refunded as EMC, and you move to a new area. Chat shows the EMC gained and the new balance.
- **Commands for poking around:** `/worldborder get`, and F3 for chunk coordinates.

**Note:** the pack uses the Prestige mod release that `pack/mods/mcincremental-prestige.pw.toml` pins. Features merged after that release only show up once a new release is cut and the pack is bumped to it (see `CLAUDE.md`).

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
