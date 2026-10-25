// EMC economy research dump (scratch only, not part of the pack).
const out = s => console.info('[ECON] ' + s)

let recipesDumped = true
ServerEvents.recipes(e => {
  if (recipesDumped) return
  recipesDumped = true
  const types = ['gtceu:circuit_assembler', 'gtceu:assembly_line', 'gtceu:assembler', 'minecraft:crafting_shaped', 'minecraft:crafting_shapeless',
                 'gtceu:laser_engraver', 'gtceu:cutter', 'gtceu:forming_press', 'gtceu:chemical_reactor', 'gtceu:large_chemical_reactor',
                 'gtceu:electric_blast_furnace', 'gtceu:fusion_reactor']
  types.forEach(t => {
    e.forEachRecipe({ type: t }, r => {
      const id = String(r.getId())
      if (t.startsWith('minecraft:') && !id.startsWith('gtceu:')) return
      out('RECIPE ' + id + ' ' + r.json.toString())
    })
  })
})

ServerEvents.loaded(e => {
  var server = e.server
  server.runCommandSilent('reload')
  server.scheduleInTicks(140, () => {
    try {
      var ECON_REG = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')
      var ECON_EMC = Java.loadClass('moze_intel.projecte.api.proxy.IEMCProxy')
      var ECON_II = Java.loadClass('moze_intel.projecte.api.ItemInfo')
      // 1. EMC of every item
      var n = 0
      ECON_REG.ITEM.keySet().forEach(k => {
        var id = String(k)
        var v = 0
        try { v = ECON_EMC.INSTANCE['getValue(moze_intel.projecte.api.ItemInfo)'](ECON_II.fromStack(Item.of(id))) } catch (x) { v = -1 }
        out('EMC ' + id + ' ' + v)
        n++
      })
      out('EMC_COUNT ' + n)
      // 2. GT recycling material info
      var ECON_IMD = Java.loadClass('com.gregtechceu.gtceu.api.data.chemical.material.ItemMaterialData')
      ECON_IMD.ITEM_MATERIAL_INFO.entrySet().forEach(en => {
        var id = String(ECON_REG.ITEM.getKey(en.getKey()))
        var parts = []
        en.getValue().getMaterials().forEach(ms => {
          var m = ms.material()
          parts.push((m == null ? 'null' : String(m.getName())) + '=' + (Number(ms.amount()) / 3628800))
        })
        out('MATINFO ' + id + ' ' + parts.join(','))
      })
      // 3. Ore scan: 3x3 chunk areas centred on GT grid chunks (x,z multiples of 3)
      var level = server.overworld()
      var regions = [[60, 60], [-120, 90], [150, -150]]
      regions.forEach(rg => {
        for (var gx = 0; gx < 5; gx++) for (var gz = 0; gz < 5; gz++) {
          var cx = rg[0] + gx * 3, cz = rg[1] + gz * 3
          var counts = {}
          for (var dx = -1; dx <= 1; dx++) for (var dz = -1; dz <= 1; dz++) {
            var chunk = level.getChunk(cx + dx, cz + dz)
            var secs = chunk.getSections()
            for (var i = 0; i < secs.length; i++) {
              var s = secs[i]
              if (s.hasOnlyAir()) continue
              s.getStates().count((state, c) => {
                var bid = String(ECON_REG.BLOCK.getKey(state.getBlock()))
                counts[bid] = (counts[bid] || 0) + c
              })
            }
          }
          var biome = String(level.getBiome(new BlockPos(cx * 16 + 8, 64, cz * 16 + 8)).unwrapKey().get().location())
          out('AREA ' + cx + ',' + cz + ' ' + biome + ' ' + JSON.stringify(counts))
        }
      })
      out('DONE')
    } catch (err) {
      out('ERR ' + err)
    } finally {
      server.runCommandSilent('stop')
    }
  })
})
