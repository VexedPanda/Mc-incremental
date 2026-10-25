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

// Paths (relative to the server directory) and classes used below.
const SMOKE_EMC_FILE = 'config/ProjectE/custom_emc.json'
const SMOKE_FLUID_EMC_FILE = 'kubejs/data/mcincremental_prestige/fluid_emc/fluids.json'
const SMOKE_GT_CONFIG = Java.loadClass('com.gregtechceu.gtceu.config.ConfigHolder')
const smokeGTRecipe = Java.loadClass('com.gregtechceu.gtceu.api.recipe.GTRecipe')
const smokeGTItemCap = Java.loadClass('com.gregtechceu.gtceu.api.capability.recipe.ItemRecipeCapability').CAP
const smokeEmcProxy = Java.loadClass('moze_intel.projecte.api.proxy.IEMCProxy')
const smokeItemInfo = Java.loadClass('moze_intel.projecte.api.ItemInfo')
const smokeRegistries = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')
const smokeRL = Java.loadClass('net.minecraft.resources.ResourceLocation')
const smokeFluidEmc = Java.loadClass('io.github.vexedpanda.mcincremental.prestige.emc.FluidEmc')

// Thresholds.
// The EMC data file has ~3,900 generated entries (#55); far fewer means it was truncated or mis-parsed.
const SMOKE_MIN_EMC_ENTRIES = 2000
// Diesel is a refined GT fuel; below one iron ingot (256) it would be near-free to bank.
const SMOKE_MIN_DIESEL_EMC = 256
// Lava plus at least one GT fuel must resolve to a bucket, so the check can't pass vacuously.
const SMOKE_MIN_BUCKETS_CHECKED = 2
// #55: ProjectE's default emerald value (on the c:gems/emerald tag), back in force now nothing pins it.
const SMOKE_DEFAULT_EMERALD_EMC = 16384
// #55: at least this many GT ore blocks and raw ores must be compared with their material, so the
// ore-vs-ingot check can't pass vacuously (GT registers about 1,800).
const SMOKE_MIN_ORES_CHECKED = 1000
// #55: what may stay at 0 EMC. Every other registered item and fluid must have a value.
// Items no survival player can obtain, or that ProjectE values only through data components:
const SMOKE_ZERO_EMC_ITEMS = [
  /^minecraft:air$/,
  /_spawn_egg$/,                                                     // creative only
  /^minecraft:(command_block|chain_command_block|repeating_command_block|command_block_minecart|structure_block|structure_void|jigsaw|barrier|light|debug_stick|knowledge_book)$/, // creative/technical
  /^gtceu:(creative_.*|test_mui|gui_module|portable_debug_scanner|(overworld|the_nether|the_end)_marker)$/, // GT creative/technical
  /^minecraft:(bedrock|end_portal_frame|spawner|trial_spawner|vault|budding_amethyst|reinforced_deepslate|farmland|frogspawn|petrified_oak_slab|player_head|bundle|infested_.*)$/, // no survival way to pick up (bundle: experimental)
  /^minecraft:(potion|splash_potion|lingering_potion|tipped_arrow|ominous_bottle)$/, // valued per potion content (data components), not as a bare item
  /^gtceu:.*_(energy_converter|solar_panel|item_passthrough_hatch|fluid_passthrough_hatch)$/, // GT ships no recipe for these
  /^gtceu:(uev|uiv|uxv|opv|max)_machine_casing$/,                    // GT ships no recipe beyond UHV
  /^gtceu:(atomic_casing|industrial_steam_casing|zero_point_module|compressed_clay|treated_wood_hanging_sign|sus_record|purple_drink)$/, // no recipe or loot
  /^gtceu:.*_(fluid_drilling_rig|bedrock_ore_miner)$/,               // recipes removed (#40, ADR-0005)
  /^projecte:(collector_mk[123]|tome)$/,                             // recipes removed (#40) / disabled
  /^projecte:transmutation_tablet$/,                                 // 0 on purpose: the Prestige mod hands it out
  /^gtceu:(bromine|mc_guffium_239|uu_matter|raw_oil|light_oil)_bucket$/ // buckets of the fluids below
]
// Fluids nothing in this Pack makes (no ore, no recipe; oil only came from the removed Fluid Drilling Rig):
const SMOKE_ZERO_EMC_FLUIDS = ['minecraft:empty', 'minecraft:water', 'gtceu:bromine', 'gtceu:mc_guffium_239',
  'gtceu:uu_matter', 'gtceu:raw_oil', 'gtceu:light_oil', 'gtceu:potion']
// How long to wait for ProjectE's EMC map after /reload before failing.
const SMOKE_EMC_WAIT_SECONDS = 60

// EMC helpers. getValue/getSellValue are overloaded, so Rhino needs the explicit method signature.
const smokeEmc = id => smokeEmcProxy.INSTANCE['getValue(moze_intel.projecte.api.ItemInfo)'](smokeItemInfo.fromStack(Item.of(id)))
const smokeSellEmc = id => smokeEmcProxy.INSTANCE['getSellValue(moze_intel.projecte.api.ItemInfo)'](smokeItemInfo.fromStack(Item.of(id)))

// Item ids a recipe outputs. GT machine recipes keep outputs in their own maps
// (getResultItem is empty for them); every other recipe type uses getResultItem.
const smokeRecipeOutputIds = (server, holder) => {
  var recipe = holder.value()
  var ids = []
  var addStack = stack => {
    if (!stack.isEmpty()) ids.push(String(smokeRegistries.ITEM.getKey(stack.getItem())))
  }
  if (recipe instanceof smokeGTRecipe) {
    [recipe.outputs, recipe.tickOutputs].forEach(map => {
      var contents = map.get(smokeGTItemCap)
      if (contents == null) return
      for (var i = 0; i < contents.size(); i++) {
        var stacks = contents.get(i).content().getItems()
        for (var j = 0; j < stacks.length; j++) addStack(stacks[j])
      }
    })
  } else {
    addStack(recipe.getResultItem(server.registryAccess()))
  }
  return ids
}
const smokeEachRecipe = (server, fn) => {
  var it = server.recipeManager.getRecipes().iterator()
  while (it.hasNext()) fn(it.next())
}

const SMOKE_TEST_ASSERTIONS = [
  {
    name: 'vanilla crafting table recipe exists',
    check: server => server.recipeManager.byKey('minecraft:crafting_table').isPresent()
  },
  {
    name: 'GT keeps vanilla ore gen (thin baseline): removeVanillaOreGen=false',
    check: () => SMOKE_GT_CONFIG.INSTANCE.worldgen.oreVeins.removeVanillaOreGen === false
  },
  {
    name: 'GT bedrock ore veins off: doBedrockOres=false',
    check: () => SMOKE_GT_CONFIG.INSTANCE.machines.doBedrockOres === false
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
    name: '#40 no recipe of any type outputs a free-resource item (FREE_RESOURCE_ITEMS)',
    check: server => {
      // Guard against a vacuous pass: the output reader must see a vanilla and a GT output.
      var probe = (id, item) => {
        var holder = server.recipeManager.byKey(id)
        if (!holder.isPresent() || smokeRecipeOutputIds(server, holder.get()).indexOf(item) < 0) throw 'cannot read outputs of ' + id
      }
      probe('minecraft:crafting_table', 'minecraft:crafting_table')
      probe('gtceu:rock_breaker/cobblestone', 'minecraft:cobblestone')
      var banned = global.FREE_RESOURCE_ITEMS.map(id => String(id))
      var found = []
      smokeEachRecipe(server, holder => {
        smokeRecipeOutputIds(server, holder).forEach(id => {
          if (banned.indexOf(id) >= 0) found.push(String(holder.id()) + ' -> ' + id)
        })
      })
      if (found.length > 0) throw found.join(', ')
      return true
    }
  },
  {
    name: '#40 GT Rock Breaker outputs stone variants only (no ore, raw ore, crushed ore or dust)',
    check: server => {
      var checked = 0
      var bad = []
      smokeEachRecipe(server, holder => {
        if (String(holder.id()).indexOf('gtceu:rock_breaker/') !== 0) return
        checked++
        smokeRecipeOutputIds(server, holder).forEach(id => {
          if (/(^|[:_])(ore|ores|raw|crushed|purified|impure)(_|$)|dust/.test(id)) bad.push(String(holder.id()) + ' -> ' + id)
        })
      })
      if (checked === 0) throw 'no rock_breaker recipes found'
      if (bad.length > 0) throw bad.join(', ')
      return true
    }
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
      const file = JsonIO.read(SMOKE_EMC_FILE)
      if (file == null) throw 'EMC data file missing'
      const entries = file.entries
      if (entries.length < SMOKE_MIN_EMC_ENTRIES) throw 'only ' + entries.length + ' entries'
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
        const sell = smokeSellEmc(id)
        if (smokeEmc(id) <= 0 || sell != smokeEmc(id)) throw id + ' sells for ' + sell + ', EMC ' + smokeEmc(id)
      })
      return true
    }
  },
  {
    name: 'Fluid EMC: file parses, ids are registered fluids, water is free',
    check: server => {
      const file = JsonIO.read(SMOKE_FLUID_EMC_FILE)
      if (file == null) throw 'fluid EMC file missing'
      const values = file.emc_per_1000_mb
      Object.keys(values).forEach(id => {
        if (!smokeRegistries.FLUID.containsKey(smokeRL.parse(id))) throw 'unregistered fluid ' + id
        if (!(values[id] >= 0)) throw id + ' has bad value ' + values[id]
      })
      if (values['minecraft:water'] !== 0) throw 'water is ' + values['minecraft:water']
      if (!(values['gtceu:diesel'] >= SMOKE_MIN_DIESEL_EMC)) throw 'diesel is ' + values['gtceu:diesel']
      return true
    }
  },
  {
    name: 'Fluid EMC: each filled bucket is worth an empty bucket plus its fluid value',
    check: server => {
      const values = JsonIO.read(SMOKE_FLUID_EMC_FILE).emc_per_1000_mb
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
      if (checked < SMOKE_MIN_BUCKETS_CHECKED) throw 'only ' + checked + ' buckets checked'
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
    name: '#55 EMC data file pins no tags, so ProjectE\'s tag defaults (emerald, ingots, gems) apply',
    check: server => {
      JsonIO.read(SMOKE_EMC_FILE).entries.forEach(e => {
        if (e.tag) throw 'tag pinned: ' + e.tag
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
      const lava = JsonIO.read(SMOKE_FLUID_EMC_FILE).emc_per_1000_mb['minecraft:lava']
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
    name: '#47/#55 ProjectE Philosopher\'s Stone conversions exist: the 8 restored by #47, plus coal_to_charcoal',
    check: server => {
      // #41 removed 8 conversions and #47 restored them; #53 removed the two emerald ones and #55 restored them.
      // coal_to_charcoal was never removed and is checked as a canary that the conversions datapack loaded at all.
      ;['gold_ingot_to_diamond', 'diamond_to_gold_ingot', 'iron_ingot_to_gold_ingot', 'gold_ingot_to_iron_ingot',
        'iron_ingot_to_ender_pearl', 'redstone_to_lava', 'emerald_to_diamond', 'diamond_to_emerald',
        'coal_to_charcoal'].forEach(id => {
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
    name: '#47 water stays free: Evertide Amulet and its recipe exist',
    check: server => Item.exists('projecte:evertide_amulet') &&
      server.recipeManager.byKey('projecte:evertide_amulet').isPresent()
  },
  {
    name: 'Transmutation Tablet is worth 0 EMC (the prestige mod hands it out for free)',
    check: server => {
      if (smokeEmc('projecte:transmutation_tablet') != 0) throw 'EMC is ' + smokeEmc('projecte:transmutation_tablet')
      return true
    }
  },
  // --- end #47 ---

  // --- #55: every obtainable item and fluid has EMC; ores in line with their ingots; GT values derived (#52) ---
  {
    name: '#55 emerald has ProjectE\'s default value (' + SMOKE_DEFAULT_EMERALD_EMC + ')',
    check: server => {
      if (smokeEmc('minecraft:emerald') != SMOKE_DEFAULT_EMERALD_EMC) throw 'emerald EMC is ' + smokeEmc('minecraft:emerald')
      return true
    }
  },
  {
    name: '#55 every registered item has EMC > 0, except the allow-list (SMOKE_ZERO_EMC_ITEMS)',
    check: server => {
      const zero = []
      smokeRegistries.ITEM.keySet().forEach(rl => {
        const id = String(rl)
        if (SMOKE_ZERO_EMC_ITEMS.some(re => re.test(id))) return
        if (!(smokeEmc(id) > 0)) zero.push(id)
      })
      if (zero.length > 0) throw zero.length + ' items at 0: ' + zero.slice(0, 60).join(', ')
      return true
    }
  },
  {
    name: '#55 every fluid has EMC > 0 at runtime (fluid_emc), except water and SMOKE_ZERO_EMC_FLUIDS',
    check: server => {
      const zero = []
      smokeRegistries.FLUID.keySet().forEach(rl => {
        const f = smokeRegistries.FLUID.get(rl)
        const id = String(smokeRegistries.FLUID.getKey(smokeFluidEmc.source(f)))
        if (SMOKE_ZERO_EMC_FLUIDS.indexOf(id) >= 0) return
        if (!(smokeFluidEmc.valuePerBucket(f) > 0)) zero.push(String(rl))
      })
      if (zero.length > 0) throw zero.length + ' fluids at 0: ' + zero.slice(0, 60).join(', ')
      return true
    }
  },
  {
    name: '#55 each GT ore block and raw ore is worth at least its material\'s ingot (or gem, or dust)',
    check: server => {
      // Material forms by tag: c:ores/<m> and c:raw_materials/<m> against c:ingots/<m>, c:gems/<m>, else c:dusts/<m>.
      let checked = 0
      const bad = []
      const best = m => {
        let v = 0
        ;['c:ingots/', 'c:gems/'].forEach(t => {
          if (!String(Ingredient.of('#' + t + m).itemIds).includes('minecraft:barrier')) {
            Ingredient.of('#' + t + m).itemIds.forEach(id => { v = Math.max(v, smokeEmc(id)) })
          }
        })
        if (v == 0 && !String(Ingredient.of('#c:dusts/' + m).itemIds).includes('minecraft:barrier')) {
          Ingredient.of('#c:dusts/' + m).itemIds.forEach(id => { v = Math.max(v, smokeEmc(id)) })
        }
        return v
      }
      smokeRegistries.ITEM.getTags().forEach(pair => {
        const tag = String(pair.getFirst().location())
        const match = /^c:(ores|raw_materials)\/(.+)$/.exec(tag)
        if (!match) return
        const unit = best(match[2])
        if (unit == 0) return
        pair.getSecond().forEach(h => {
          const id = String(h.unwrapKey().get().location())
          if (!id.startsWith('gtceu:')) return
          checked++
          if (!(smokeEmc(id) >= unit)) bad.push(id + ' ' + smokeEmc(id) + ' < ' + unit)
        })
      })
      if (checked < SMOKE_MIN_ORES_CHECKED) throw 'only ' + checked + ' ores checked'
      if (bad.length > 0) throw bad.length + ' ores below their ingot: ' + bad.slice(0, 40).join(', ')
      return true
    }
  },
  {
    name: '#52/#55 GT machines and circuits are valued from their recipes: MV macerator > LV macerator > 0, good integrated circuit > 0',
    check: server => {
      const lv = smokeEmc('gtceu:lv_macerator')
      const mv = smokeEmc('gtceu:mv_macerator')
      if (!(lv > 0 && mv > lv)) throw 'lv_macerator ' + lv + ', mv_macerator ' + mv
      if (!(smokeEmc('gtceu:good_integrated_circuit') > 0)) throw 'good_integrated_circuit has no EMC'
      return true
    }
  },
  {
    name: '#55 the EMC data file no longer pins what the GT recipe mapper derives (circuits, LV parts, LV casing and hull)',
    check: server => {
      const derived = ['gtceu:vacuum_tube', 'gtceu:resistor', 'gtceu:basic_electronic_circuit',
        'gtceu:good_electronic_circuit', 'gtceu:good_integrated_circuit', 'gtceu:lv_electric_motor',
        'gtceu:lv_electric_pump', 'gtceu:lv_electric_piston', 'gtceu:lv_conveyor_module', 'gtceu:lv_robot_arm',
        'gtceu:lv_machine_casing', 'gtceu:lv_machine_hull', 'gtceu:lv_macerator', 'gtceu:mv_macerator']
      JsonIO.read(SMOKE_EMC_FILE).entries.forEach(e => {
        if (derived.indexOf(String(e.id)) >= 0) throw 'pinned: ' + e.id
      })
      derived.forEach(id => { if (!(smokeEmc(id) > 0)) throw id + ' has no EMC' })
      return true
    }
  },
  // --- end #55 ---

  // --- #46: view and simulation distance default to the Run area plus one chunk (radius 2) ---
  // Values come from the Pack's shipped server.properties (the smoke script keeps them).
  // Simulation distance has no server-side clamp; 2 is the lowest value that keeps the
  // whole 3x3 Run area entity-ticking from any chunk inside it.
  {
    name: '#46 server view distance is 2',
    check: server => {
      if (server.playerList.getViewDistance() != 2) throw 'playerList view distance ' + server.playerList.getViewDistance()
      if (server.getProperties().viewDistance != 2) throw 'server.properties view-distance ' + server.getProperties().viewDistance
      return true
    }
  },
  {
    name: '#46 server simulation distance is 2',
    check: server => {
      if (server.playerList.getSimulationDistance() != 2) throw 'playerList simulation distance ' + server.playerList.getSimulationDistance()
      if (server.getProperties().simulationDistance != 2) throw 'server.properties simulation-distance ' + server.getProperties().simulationDistance
      return true
    }
  },
  // --- end #46 ---

  // --- #42: prestige mod (mcincremental_prestige v0.1.0) ---
  {
    name: '#42 Prestige item is registered and its recipe exists',
    check: server => {
      if (!smokeRegistries.ITEM.containsKey(smokeRL.parse('mcincremental_prestige:prestige'))) throw 'item not registered'
      if (!server.recipeManager.byKey('mcincremental_prestige:prestige').isPresent()) throw 'recipe missing'
      return true
    }
  },
  {
    name: '#42 EMC barrel block is registered and its recipe exists',
    check: server => {
      if (!smokeRegistries.BLOCK.containsKey(smokeRL.parse('mcincremental_prestige:emc_barrel'))) throw 'block not registered'
      if (!server.recipeManager.byKey('mcincremental_prestige:emc_barrel').isPresent()) throw 'recipe missing'
      return true
    }
  }
  // --- end #42 ---
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
    // wait (bounded) until cobblestone has EMC before asserting anything. If it never
    // gets EMC, fail once with a clear reason instead of every EMC assertion failing.
    let attempts = 0
    const waitForEmc = () => {
      let done = true
      try {
        if (smokeEmc('minecraft:cobblestone') == 0) {
          if (++attempts < SMOKE_EMC_WAIT_SECONDS) {
            done = false
            server.scheduleInTicks(20, waitForEmc)
            return
          }
          console.info('SMOKE-TEST FAILED: EMC map not built (cobblestone EMC still 0 after ' + SMOKE_EMC_WAIT_SECONDS + 's)')
          console.info('SMOKE-TEST RESULT: FAIL (EMC map not built)')
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
