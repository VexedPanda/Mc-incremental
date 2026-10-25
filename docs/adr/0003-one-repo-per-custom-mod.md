# Custom code lives in one repo per mod; this repo only assembles the Pack

Glue that KubeJS can express stays in this repo's Pack. Anything that needs Java (the Prestige controller, an EMC tank, and so on) is a separate NeoForge mod, each in its own repository with its own build and releases. This repo consumes their released jars like any other mod. We chose this over a monorepo so each mod can be versioned, reused across PoCs and published independently, and so Pack CI stays fast with no Java build.
