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
    name: 'Fluid EMC: file parses, ids are registered fluids, water is free',
    check: server => {
      const file = JsonIO.read('kubejs/data/mcincremental_prestige/fluid_emc/fluids.json')
      if (file == null) throw 'fluid EMC file missing'
      const values = file.emc_per_1000_mb
      Object.keys(values).forEach(id => {
        if (!smokeRegistries.FLUID.containsKey(smokeRL.parse(id))) throw 'unregistered fluid ' + id
        if (!(values[id] >= 0)) throw id + ' has bad value ' + values[id]
      })
      if (values['minecraft:water'] !== 0) throw 'water is ' + values['minecraft:water']
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
  // --- end #41 ---

  // --- #47 ProjectE default EMC values; conversions and Volcanite Amulet restored ---
  {
    name: '#47 EMC: vanilla items have ProjectE default values (block = 9 ingots)',
    check: server => {
      const expected = {
        'minecraft:iron_ingot': 256,
        'minecraft:gold_ingot': 2048,
        'minecraft:copper_ingot': 128,
        'minecraft:diamond': 8192,
        'minecraft:ender_pearl': 1024,
        'minecraft:redstone': 64,
        'minecraft:bucket': 768
      }
      Object.keys(expected).forEach(id => {
        if (smokeEmc(id) != expected[id]) throw id + ' EMC is ' + smokeEmc(id) + ', expected ' + expected[id]
      })
      ;['iron', 'gold', 'copper'].forEach(m => {
        const block = smokeEmc('minecraft:' + m + '_block')
        const ingot = smokeEmc('minecraft:' + m + '_ingot')
        if (block != 9 * ingot) throw m + '_block EMC is ' + block + ', ingot ' + ingot
      })
      return true
    }
  },
  {
    name: '#47 EMC data file pins no tags and no vanilla items but those GT hides from ProjectE',
    check: server => {
      // GT's recipes for these need tools or machines ProjectE can't value, so they are pinned at ProjectE's defaults.
      const allowed = ['minecraft:bucket', 'minecraft:lava_bucket', 'minecraft:iron_block', 'minecraft:gold_block',
        'minecraft:copper_block']
      JsonIO.read('config/ProjectE/custom_emc.json').entries.forEach(e => {
        if (e.tag) throw 'tag pinned: ' + e.tag
        if (String(e.id).indexOf('minecraft:') === 0 && allowed.indexOf(String(e.id)) < 0) throw 'vanilla item pinned: ' + e.id
      })
      return true
    }
  },
  {
    name: '#47 EMC: GT metals match ProjectE default metal values; GT key parts have EMC',
    check: server => {
      const expected = {
        'gtceu:tin_ingot': 256,
        'gtceu:bronze_ingot': 160,
        'gtceu:lead_ingot': 512,
        'gtceu:silver_ingot': 512,
        'gtceu:nickel_ingot': 1024,
        'gtceu:iron_dust': 256,
        'gtceu:iron_plate': 256,
        'gtceu:gold_plate': 2048,
        'gtceu:copper_plate': 128
      }
      Object.keys(expected).forEach(id => {
        if (smokeEmc(id) != expected[id]) throw id + ' EMC is ' + smokeEmc(id) + ', expected ' + expected[id]
      })
      ;['steel', 'bronze', 'wrought_iron', 'aluminium'].forEach(m => {
        const ingot = smokeEmc('gtceu:' + m + '_ingot')
        if (!(ingot > 0) || smokeEmc('gtceu:' + m + '_dust') != ingot || smokeEmc('gtceu:' + m + '_plate') != ingot) {
          throw m + ' ingot/dust/plate EMC ' + ingot + '/' + smokeEmc('gtceu:' + m + '_dust') + '/' + smokeEmc('gtceu:' + m + '_plate')
        }
      })
      if (!(smokeEmc('gtceu:steel_ingot') > smokeEmc('minecraft:iron_ingot'))) throw 'steel is not worth more than iron'
      ;['gtceu:basic_electronic_circuit', 'gtceu:lv_electric_motor', 'gtceu:lv_machine_casing',
        'gtceu:lv_machine_hull', 'gtceu:lp_steam_solid_boiler'].forEach(id => {
        if (!(smokeEmc(id) > 0)) throw id + ' has no EMC'
      })
      return true
    }
  },
  {
    name: '#47 Fluid EMC: lava equals ProjectE default lava bucket (832) minus empty bucket (768)',
    check: server => {
      // ProjectE defaults: bucket = 3 iron ingots; lava bucket = bucket + redstone (conversions/redstone_to_lava).
      const lava = JsonIO.read('kubejs/data/mcincremental_prestige/fluid_emc/fluids.json').emc_per_1000_mb['minecraft:lava']
      const bucket = smokeEmc('minecraft:bucket')
      const lavaBucket = smokeEmc('minecraft:lava_bucket')
      if (bucket != 3 * smokeEmc('minecraft:iron_ingot') || lavaBucket != bucket + smokeEmc('minecraft:redstone')) {
        throw 'bucket ' + bucket + ', lava bucket ' + lavaBucket
      }
      if (lava != 64 || lava != lavaBucket - bucket) throw 'lava is ' + lava + ', expected ' + lavaBucket + ' - ' + bucket
      return true
    }
  },
  {
    name: '#47 ProjectE Philosopher\'s Stone conversions exist (e.g. 4 gold -> diamond)',
    check: server => {
      ;['gold_ingot_to_diamond', 'diamond_to_gold_ingot', 'iron_ingot_to_gold_ingot',
        'gold_ingot_to_iron_ingot', 'iron_ingot_to_ender_pearl', 'diamond_to_emerald',
        'emerald_to_diamond', 'redstone_to_lava', 'coal_to_charcoal'].forEach(id => {
        if (!server.recipeManager.byKey('projecte:conversions/' + id).isPresent()) throw id + ' missing'
      })
      return true
    }
  },
  {
    name: '#47 Volcanite Amulet and Gem Chestplate are craftable',
    check: server => {
      // ProjectE ships the Gem Chestplate under one of two ids, depending on its full_klein_stars config.
      const outputs = {
        'projecte:volcanite_amulet': ['projecte:volcanite_amulet'],
        'projecte:gem_chestplate': ['projecte:gem_chestplate', 'projecte:full_star_gem_chestplate']
      }
      Object.keys(outputs).forEach(item => {
        const found = outputs[item].some(id => {
          const holder = server.recipeManager.byKey(id)
          if (!holder.isPresent()) return false
          const out = holder.get().value().getResultItem(server.registryAccess()).getItem()
          return String(smokeRegistries.ITEM.getKey(out)) === item
        })
        if (!found) throw 'no recipe crafts ' + item
      })
      return true
    }
  },
  {
    name: '#45 water stays free: Evertide Amulet and its recipe exist',
    check: server => Item.exists('projecte:evertide_amulet') &&
      server.recipeManager.byKey('projecte:evertide_amulet').isPresent()
  }
  // --- end #47 ---
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
