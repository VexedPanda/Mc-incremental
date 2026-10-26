// No free resource generation (ADR-0005, issue #40).
//
// Removes the recipes for machines and items that create value from nothing.
// The items stay registered (worlds and other recipes keep working) but become
// unobtainable; client_scripts/hide_free_resources.js hides them in EMI.
//
// Allowed free sources stay: air (GT Gas Collector), water (pumps, infinite
// water cover) and stone variants (GT Rock Breaker).
//
// Not covered here, because they don't exist in the Pack:
// - GT Bedrock Ore Miner has no crafting recipe in the pinned GTCEu snapshot;
//   it is only hidden.
// - ProjectE 1.21.1 has no power flower item (the "power flower" is the
//   collector + relay setup, so removing collectors is enough). Relays and
//   condensers only move or convert EMC and stay.
// - No mod in the Pack adds a chunk loader. The smoke test fails if one appears.

ServerEvents.recipes(event => {
  // Every recipe that outputs a free-resource machine (startup_scripts/free_resource_items.js):
  // GT Fluid Drilling Rig (MV/HV/EV, oil/gas/lava from bedrock fluid veins), GT Bedrock Ore
  // Miner (guard in case a recipe for it appears) and ProjectE Energy Collectors MK1-3 (EMC
  // from sunlight). Removing by output catches every recipe type, so no id match is needed.
  global.FREE_RESOURCE_ITEMS.forEach(item => event.remove({ output: item }))

  // GT centrifuge: stone dust -> metal mixture etc. (cobble into titanium, chrome ...).
  // Not a machine, so it is removed by recipe id.
  event.remove({ id: 'gtceu:centrifuge/stone_dust_separation' })
})
