// Items that generate resources from nothing (ADR-0005, issue #40).
// Shared by server_scripts/no_free_resources.js (recipe removal) and
// client_scripts/hide_free_resources.js (EMI hiding).
global.FREE_RESOURCE_ITEMS = [
  'gtceu:mv_fluid_drilling_rig',
  'gtceu:hv_fluid_drilling_rig',
  'gtceu:ev_fluid_drilling_rig',
  'gtceu:mv_bedrock_ore_miner',
  'gtceu:hv_bedrock_ore_miner',
  'gtceu:ev_bedrock_ore_miner',
  'projecte:collector_mk1',
  'projecte:collector_mk2',
  'projecte:collector_mk3'
  // The Volcanite Amulet (lava from nothing) stays (#47, undoing #45): lava is worth
  // only 64 EMC per bucket at ProjectE's defaults, below the 100+ EMC exploit threshold.
]
