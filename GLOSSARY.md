# Mc-incremental

A Minecraft modpack played as an incremental game: each Run is starved of resources, and the player Prestiges to start a fresh Run while keeping their Knowledge.

## Language

### The Pack

**Pack**:
The curated set of mods, configs, scripts and quests this repo produces and players install.
_Avoid_: Modpack (fine in prose), instance, profile

**PoC**:
One trial combination of Content mod, carry-over mechanism and rules, built to test whether the loop is fun. Several PoCs may exist side by side.
_Avoid_: Prototype, variant, edition

**Content mod**:
The mod whose own progression is the primary gameplay within a Run; it must be fun and rewarding without the Prestige loop.
_Avoid_: Centrepiece mod (earlier name), core mod (means something else in Minecraft modding), main mod

**Support mod**:
Any mod in the Pack that isn't the Content mod, included either to feed its progression or for quality of life.
_Avoid_: Addon (reserved for mods that extend a specific other mod)

**Progression layer**:
The Pack's own additions on top of its mods (questbook, recipe changes, staged unlocks) that tie them into one Progression.
_Avoid_: Integration, glue

### The loop

**Run**:
The span of play between two Prestiges, confined to one Run area and limited by the resources it holds.
_Avoid_: Cycle, life, loop, playthrough

**Run area**:
The small, fixed patch of an ordinarily generated world that a Run is confined to.
_Avoid_: Plot, island, claim, chunk (a Run area is made of chunks)

**Prestige**:
Deliberately ending the current Run and starting a new one in a fresh, never-visited Run area, keeping only Knowledge (and whatever else is designed to carry over).
_Avoid_: Reset, rebirth, ascension, new game+

**Prestige sweep**:
The step of a Prestige that converts everything the player added to the Run area (anything not matching the original worldgen) into EMC and removes it, so nothing valuable stays behind.
_Avoid_: Cleanup, refund, salvage

**Knowledge**:
The set of resources a player has learned and can recreate from EMC; it belongs to the player, not the world, so it survives Prestige.
_Avoid_: Unlocks, research, memory

**EMC barrel**:
A placed block linked to its owner's EMC balance: it hands out one configured learned resource (item or fluid) paid for from the balance, and converts anything piped into it into EMC.
_Avoid_: EMC tank, condenser (ProjectE's condenser works the other way), drawer

**Progression**:
The path a player takes through the Content mod within a Run, gated by effort, complexity and the resources available rather than by waiting.
_Avoid_: Grind

**Meta progression**:
Progress that survives Prestige and makes each later Run faster or deeper.
_Avoid_: Permanent upgrades, account progress
