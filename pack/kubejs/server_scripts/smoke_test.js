// TEST-ONLY: server smoke test assertions, run by scripts/smoke-test.sh.
//
// Inert in normal play: it does nothing unless `smoke-test.json` exists in the
// server directory, which only scripts/smoke-test.sh writes. To strip it from
// player installs instead, add this path to pack/.packwizignore (the smoke test
// would then need to copy it into the server itself).
//
// Contract with scripts/smoke-test.sh: after the server has loaded (and a /reload
// has built ProjectE's EMC map), log exactly
// one of these lines, then stop the server:
//   SMOKE-TEST RESULT: PASS
//   SMOKE-TEST RESULT: FAIL
//
// Assertions check external outcomes in the running server (a recipe exists or
// not, an item is registered or not, an EMC value), never script internals.
// Each is { name, check(server) } where check returns true, or returns false /
// throws to fail.

// Helpers for EMC assertions. getValue/getSellValue are overloaded, so Rhino needs the
// explicit method signature.
const smokeEmcProxy = Java.loadClass('moze_intel.projecte.api.proxy.IEMCProxy')
const smokeItemInfo = Java.loadClass('moze_intel.projecte.api.ItemInfo')
const smokeRegistries = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')
const smokeRL = Java.loadClass('net.minecraft.resources.ResourceLocation')
const smokeEmc = id => smokeEmcProxy.INSTANCE['getValue(moze_intel.projecte.api.ItemInfo)'](smokeItemInfo.fromStack(Item.of(id)))

const SMOKE_TEST_ASSERTIONS = [
  {
    name: 'vanilla crafting table recipe exists',
    check: server => server.recipeManager.byKey('minecraft:crafting_table').isPresent()
  },
  {
    name: 'GT keeps vanilla ore gen (thin baseline): removeVanillaOreGen=false',
    check: () => Java.loadClass('com.gregtechceu.gtceu.config.ConfigHolder')
      .INSTANCE.worldgen.oreVeins.removeVanillaOreGen === false
  },
  {
    name: 'GT bedrock ore veins off: doBedrockOres=false',
    check: () => Java.loadClass('com.gregtechceu.gtceu.config.ConfigHolder')
      .INSTANCE.machines.doBedrockOres === false
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
  },
  // --- end #40 ---

  // --- #41 EMC values (pack/config/ProjectE/custom_emc.json)
  //     and fluid EMC (pack/kubejs/data/mcincremental_prestige/fluid_emc/fluids.json) ---
  {
    name: 'EMC: key GT and renewable item values are set',
    check: server => {
      const expected = {
        'minecraft:iron_ingot': 64,
        'gtceu:steel_ingot': 128,
        'gtceu:steel_plate': 128,
        'gtceu:bronze_ingot': 80,
        'gtceu:basic_electronic_circuit': 512,
        'gtceu:lv_electric_motor': 384,
        'gtceu:lv_machine_casing': 1024,
        'gtceu:lp_steam_solid_boiler': 1024,
        'minecraft:rotten_flesh': 4
      }
      Object.keys(expected).forEach(id => {
        if (smokeEmc(id) != expected[id]) throw id + ' EMC is ' + smokeEmc(id) + ', expected ' + expected[id]
      })
      return true
    }
  },
  {
    name: 'EMC: every item in the EMC data file is registered and has exactly its listed value',
    check: server => {
      const file = JsonIO.read('config/ProjectE/custom_emc.json')
      if (file == null) throw 'EMC data file missing'
      const entries = file.entries
      if (entries.length < 40) throw 'only ' + entries.length + ' entries'
      entries.forEach(e => {
        // (no let/const in this block: Rhino reports them as redeclared on the next entry)
        if (e.tag) {
          if (String(Ingredient.of('#' + e.tag).itemIds).indexOf('minecraft:barrier') >= 0) throw 'empty tag ' + e.tag
          Ingredient.of('#' + e.tag).itemIds.forEach(id => {
            if (smokeEmc(id) != e.emc) throw id + ' (#' + e.tag + ') EMC is ' + smokeEmc(id) + ', file says ' + e.emc
          })
          return
        }
        if (!smokeRegistries.ITEM.containsKey(smokeRL.parse(e.id))) throw 'unregistered item ' + e.id
        if (smokeEmc(e.id) != e.emc) throw e.id + ' EMC is ' + smokeEmc(e.id) + ', file says ' + e.emc
      })
      return true
    }
  },
  {
    name: 'EMC: items crafted from metal tags use the Pack values, not ProjectE defaults (block = 9 ingots)',
    check: server => {
      ['iron', 'gold', 'copper'].forEach(m => {
        const block = smokeEmc('minecraft:' + m + '_block')
        const ingot = smokeEmc('minecraft:' + m + '_ingot')
        if (block != 9 * ingot) throw m + '_block EMC is ' + block + ', ingot ' + ingot
      })
      return true
    }
  },
  {
    name: 'EMC: sell value equals EMC value (lossless)',
    check: server => {
      ['gtceu:steel_ingot', 'gtceu:lv_electric_motor', 'minecraft:diamond'].forEach(id => {
        const info = smokeItemInfo.fromStack(Item.of(id))
        const sell = smokeEmcProxy.INSTANCE['getSellValue(moze_intel.projecte.api.ItemInfo)'](info)
        if (smokeEmc(id) <= 0 || sell != smokeEmc(id)) throw id + ' sells for ' + sell + ', EMC ' + smokeEmc(id)
      })
      return true
    }
  },
  {
    name: 'Fluid EMC: file parses, ids are registered fluids, water is free, lava is scarce',
    check: server => {
      const file = JsonIO.read('kubejs/data/mcincremental_prestige/fluid_emc/fluids.json')
      if (file == null) throw 'fluid EMC file missing'
      const values = file.emc_per_1000_mb
      Object.keys(values).forEach(id => {
        if (!smokeRegistries.FLUID.containsKey(smokeRL.parse(id))) throw 'unregistered fluid ' + id
        if (!(values[id] >= 0)) throw id + ' has bad value ' + values[id]
      })
      if (values['minecraft:water'] !== 0) throw 'water is ' + values['minecraft:water']
      if (!(values['minecraft:lava'] >= 256)) throw 'lava is ' + values['minecraft:lava']
      if (!(values['gtceu:diesel'] >= 256)) throw 'diesel is ' + values['gtceu:diesel']
      return true
    }
  },
  {
    name: 'Fluid EMC: each filled bucket is worth an empty bucket plus its fluid value',
    check: server => {
      const values = JsonIO.read('kubejs/data/mcincremental_prestige/fluid_emc/fluids.json').emc_per_1000_mb
      const empty = smokeEmc('minecraft:bucket')
      let checked = 0
      Object.keys(values).forEach(id => {
        const bucket = smokeRegistries.FLUID.get(smokeRL.parse(id)).getBucket()
        const bucketId = String(smokeRegistries.ITEM.getKey(bucket))
        if (bucketId == 'minecraft:air') return
        checked++
        if (smokeEmc(bucketId) != empty + values[id]) {
          throw bucketId + ' EMC is ' + smokeEmc(bucketId) + ', expected ' + empty + ' + ' + values[id]
        }
      })
      if (checked < 2) throw 'only ' + checked + ' buckets checked'
      return true
    }
  },
  {
    name: 'EMC: ProjectE fixed-ratio conversions that bypass EMC values are gone (e.g. 4 gold -> diamond)',
    check: server => {
      const ids = ['gold_ingot_to_diamond', 'diamond_to_gold_ingot', 'iron_ingot_to_gold_ingot',
        'gold_ingot_to_iron_ingot', 'iron_ingot_to_ender_pearl', 'diamond_to_emerald',
        'emerald_to_diamond', 'redstone_to_lava']
      if (!server.recipeManager.byKey('projecte:conversions/coal_to_charcoal').isPresent()) throw 'id format changed'
      ids.forEach(id => {
        if (server.recipeManager.byKey('projecte:conversions/' + id).isPresent()) throw id + ' still exists'
      })
      return true
    }
  },
  // --- end #41 ---

  // --- #45: no free lava from ProjectE amulets (ADR-0005) ---
  {
    name: '#45 no recipe crafts the Volcanite Amulet (free lava)',
    check: server => {
      if (!Item.exists('projecte:volcanite_amulet')) throw 'item id changed'
      return !server.recipeManager.getRecipeIds().anyMatch(id => String(id).includes('volcanite_amulet')) &&
        !server.recipeManager.getRecipes().stream().anyMatch(holder => {
          try {
            const out = holder.value().getResultItem(server.registryAccess()).getItem()
            return String(smokeRegistries.ITEM.getKey(out)) === 'projecte:volcanite_amulet'
          } catch (e) {
            return false // some modded recipe types have no single result item
          }
        })
    }
  },
  {
    name: '#45 water stays free: Evertide Amulet and its recipe exist',
    check: server => Item.exists('projecte:evertide_amulet') &&
      server.recipeManager.byKey('projecte:evertide_amulet').isPresent()
  }
  // --- end #45 ---
]

if (JsonIO.read('smoke-test.json') != null) {
  ServerEvents.loaded(event => {
    const server = event.server
    const runAssertions = () => {
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
    }
    // ProjectE only builds its EMC map on player join or /reload, so reload first and
    // wait (bounded) until cobblestone has EMC before asserting anything.
    let attempts = 0
    const waitForEmc = () => {
      let done = true
      try {
        if (smokeEmc('minecraft:cobblestone') == 0 && ++attempts < 60) {
          done = false
          server.scheduleInTicks(20, waitForEmc)
          return
        }
        runAssertions()
      } catch (e) {
        console.error('SMOKE-TEST RESULT: FAIL (' + e + ')')
      } finally {
        if (done) server.runCommandSilent('stop')
      }
    }
    server.runCommandSilent('reload')
    server.scheduleInTicks(20, waitForEmc)
  })
}
