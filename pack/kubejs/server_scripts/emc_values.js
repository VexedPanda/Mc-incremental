// EMC balance support (issue #41).
//
// EMC values live in config/ProjectE/custom_emc.json; fluid EMC per 1000 mB in
// kubejs/data/mcincremental_prestige/fluid_emc/fluids.json.
//
// ProjectE ships Philosopher's Stone / amulet crafting recipes that convert at
// fixed ratios tuned to its default values (8 iron = 1 gold, 4 gold = 1 diamond,
// redstone + bucket = lava bucket). With the Pack's lower renewable values they
// create EMC from nothing (4 gold = 512 EMC -> diamond = 8192 EMC), so remove them.
// Transmutation through EMC still covers these conversions at the real values.

ServerEvents.recipes(event => {
  ;['gold_ingot_to_diamond', 'diamond_to_gold_ingot', 'iron_ingot_to_gold_ingot',
    'gold_ingot_to_iron_ingot', 'iron_ingot_to_ender_pearl', 'diamond_to_emerald',
    'emerald_to_diamond', 'redstone_to_lava'
  ].forEach(id => event.remove({ id: 'projecte:conversions/' + id }))
})
