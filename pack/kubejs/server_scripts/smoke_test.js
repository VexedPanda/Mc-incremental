// TEST-ONLY: server smoke test assertions, run by scripts/smoke-test.sh.
//
// Inert in normal play: it does nothing unless `smoke-test.json` exists in the
// server directory, which only scripts/smoke-test.sh writes. To strip it from
// player installs instead, add this path to pack/.packwizignore (the smoke test
// would then need to copy it into the server itself).
//
// Contract with scripts/smoke-test.sh: after the server has loaded, log exactly
// one of these lines, then stop the server:
//   SMOKE-TEST RESULT: PASS
//   SMOKE-TEST RESULT: FAIL
//
// Assertions check external outcomes in the running server (a recipe exists or
// not, an item is registered or not, an EMC value), never script internals.
// Each is { name, check(server) } where check returns true, or returns false /
// throws to fail.

const SMOKE_TEST_ASSERTIONS = [
  {
    name: 'vanilla crafting table recipe exists',
    check: server => server.recipeManager.byKey('minecraft:crafting_table').isPresent()
  },

  // --- #40: no free resource generation (ADR-0005) ---
  // Removals match recipe ids by substring, so a wrong id format can't pass vacuously.
  {
    name: '#40 no Fluid Drilling Rig recipe',
    check: server => !server.recipeManager.getRecipeIds().anyMatch(id => String(id).includes('fluid_drilling_rig'))
  },
  {
    name: '#40 no Bedrock Ore Miner recipe (GT ships none; guard)',
    check: server => !server.recipeManager.getRecipeIds().anyMatch(id => String(id).includes('bedrock_ore_miner'))
  },
  {
    name: '#40 no stone_dust_separation recipe',
    check: server => !server.recipeManager.getRecipeIds().anyMatch(id => String(id).includes('stone_dust_separation'))
  },
  {
    name: '#40 no ProjectE Energy Collector recipe',
    check: server => !server.recipeManager.getRecipeIds().anyMatch(id => String(id).includes('collector_mk'))
  },
  {
    name: '#40 no chunk loader or power flower items registered',
    check: server => !Item.getTypeList().some(id => /chunk_?load|power_?flower/.test(String(id)))
  },
  {
    name: '#40 air: GT Gas Collector and its air recipe exist',
    check: server => Item.exists('gtceu:lv_gas_collector') &&
      server.recipeManager.byKey('gtceu:gas_collector/air').isPresent()
  },
  {
    name: '#40 water: GT pump machine and infinite water cover exist',
    check: server => Item.exists('gtceu:lv_pump') && Item.exists('gtceu:infinite_water_cover')
  },
  {
    name: '#40 cobble: GT Rock Breaker and its cobblestone recipe exist',
    check: server => Item.exists('gtceu:lv_rock_crusher') &&
      server.recipeManager.byKey('gtceu:rock_breaker/cobblestone').isPresent()
  }
  // --- end #40 ---
]

if (JsonIO.read('smoke-test.json') != null) {
  ServerEvents.loaded(event => {
    const server = event.server
    let failures = 0
    SMOKE_TEST_ASSERTIONS.forEach(assertion => {
      let ok = false
      let detail = ''
      try {
        ok = assertion.check(server) === true
      } catch (e) {
        detail = ' (' + e + ')'
      }
      if (!ok) failures++
      console.info('SMOKE-TEST ' + (ok ? 'ok    ' : 'FAILED') + ': ' + assertion.name + detail)
    })
    console.info('SMOKE-TEST RESULT: ' + (failures === 0 ? 'PASS' : 'FAIL') +
      ' (' + (SMOKE_TEST_ASSERTIONS.length - failures) + '/' + SMOKE_TEST_ASSERTIONS.length + ' assertions passed)')
    server.runCommandSilent('stop')
  })
}
