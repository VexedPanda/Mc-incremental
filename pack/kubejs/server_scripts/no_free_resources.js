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
  // GT Fluid Drilling Rig (MV/HV/EV): pulls oil, gas and lava from bedrock fluid veins.
  event.remove({ id: /fluid_drilling_rig/ })
  // GT Bedrock Ore Miner: guard in case a recipe for it appears.
  event.remove({ id: /bedrock_ore_miner/ })
  // GT centrifuge: stone dust -> metal mixture etc. (cobble into titanium, chrome ...).
  event.remove({ id: 'gtceu:centrifuge/stone_dust_separation' })
  // ProjectE Energy Collectors MK1-3: EMC from sunlight.
  event.remove({ id: /^projecte:collector_mk[123]$/ })
  // ProjectE Volcanite Amulet: places lava from nothing (#45). Its use as an
  // ingredient (Gem Chestplate, Iron Band alternative) goes with it.
  event.remove({ id: 'projecte:volcanite_amulet' })

  global.FREE_RESOURCE_ITEMS.forEach(item => event.remove({ output: item }))
})
