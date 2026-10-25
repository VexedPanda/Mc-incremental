// EMC pricing dump (VexedPanda/Mc-incremental#55; docs/research/emc-pricing/README.md). NOT part of the Pack.
//
// Append this file to a copy of pack/kubejs/server_scripts/smoke_test.js in a smoke-test server's work dir and call
// `emcPricingDump(server)` at the start of its runAssertions (after ProjectE has built its EMC map). It logs:
//   EMCDUMP <item> <emc>                         every registered item's EMC
//   FLUIDDUMP <fluid> src=<source> <emc> bucket=<item>   every fluid, its fluid_emc value and its bucket
//   TAGDUMP <tag> <item>,<item>,...              every item tag
//   RDUMP {json}                                 every recipe: inputs, outputs (c: carries data components),
//                                                chances (GT) or ingredients (vanilla)
// It relies on the smoke test's smokeRegistries, smokeEmc, smokeGTRecipe and smokeGTItemCap.
const emcpFluidEmc = Java.loadClass('io.github.vexedpanda.mcincremental.prestige.emc.FluidEmc')
const emcpFluidCap = Java.loadClass('com.gregtechceu.gtceu.api.capability.recipe.FluidRecipeCapability').CAP
const emcpItemKey = st => String(smokeRegistries.ITEM.getKey(st.getItem()))
const emcpRecipes = server => {
  let it = server.recipeManager.getRecipes().iterator()
  while (it.hasNext()) {
    let holder = it.next()
    let r = holder.value()
    let o = { id: String(holder.id()), type: String(smokeRegistries.RECIPE_TYPE.getKey(r.getType())), i: [], fi: [], o: [], fo: [] }
    try {
      if (r instanceof smokeGTRecipe) {
        o.gt = true
        let side = (map, items, fluids) => {
          let ic = map.get(smokeGTItemCap)
          if (ic != null) for (let k = 0; k < ic.size(); k++) {
            let c = ic.get(k); let sz = smokeGTItemCap.of(c.content()); let ing = sz.ingredient()
            let ids = []; let st = sz.getItems(); for (let j = 0; j < st.length; j++) if (!st[j].isEmpty()) ids.push(emcpItemKey(st[j]))
            let cust = ing.getCustomIngredient()
            let comp = false; for (let j = 0; j < st.length; j++) if (!st[j].getComponentsPatch().isEmpty()) comp = true
            items.push({ ids: ids, n: sz.count(), ch: c.chance(), mx: c.maxChance(), cu: cust == null ? null : String(cust).split("@")[0], c: comp })
          }
          let fc = map.get(emcpFluidCap)
          if (fc != null) for (let k = 0; k < fc.size(); k++) {
            let c = fc.get(k); let sz = emcpFluidCap.of(c.content()); let fl = sz.getFluids(); let ids = []
            for (let j = 0; j < fl.length; j++) ids.push(String(smokeRegistries.FLUID.getKey(fl[j].getFluid())))
            fluids.push({ ids: ids, n: sz.amount(), ch: c.chance(), mx: c.maxChance(), cl: String(sz.ingredient()).split("@")[0] })
          }
        }
        side(r.inputs, o.i, o.fi)
        side(r.outputs, o.o, o.fo)
        o.cat = r.recipeCategory == null ? null : String(r.recipeCategory.id)
      } else {
        let ings = r.getIngredients()
        for (let k = 0; k < ings.size(); k++) {
          let ing = ings.get(k); if (ing.isEmpty()) continue
          let ids = []; ing.itemIds.forEach(x => ids.push(String(x)))
          o.i.push({ ids: ids, n: 1 })
        }
        let res = r.getResultItem(server.registryAccess())
        if (!res.isEmpty()) o.o.push({ ids: [emcpItemKey(res)], n: res.getCount(), c: !res.getComponentsPatch().isEmpty() })
      }
    } catch (e) { o.err = String(e) }
    console.info('RDUMP ' + JSON.stringify(o))
  }
  console.info('RDUMP-END')
}
const emcpTags = () => {
  smokeRegistries.ITEM.getTags().forEach(pair => {
    let ids = []
    pair.getSecond().forEach(h => ids.push(String(h.unwrapKey().get().location())))
    console.info('TAGDUMP ' + String(pair.getFirst().location()) + ' ' + ids.join(','))
  })
  console.info('TAGDUMP-END')
}
const emcpItemsAndFluids = () => {
  smokeRegistries.ITEM.keySet().forEach(rl => console.info('EMCDUMP ' + String(rl) + ' ' + smokeEmc(String(rl))))
  smokeRegistries.FLUID.keySet().forEach(rl => {
    const f = smokeRegistries.FLUID.get(rl)
    const src = emcpFluidEmc.source(f)
    console.info('FLUIDDUMP ' + String(rl) + ' src=' + String(smokeRegistries.FLUID.getKey(src)) + ' ' +
      emcpFluidEmc.valuePerBucket(f) + ' bucket=' + String(smokeRegistries.ITEM.getKey(f.getBucket())))
  })
  console.info('EMCDUMP-END')
}
const emcPricingDump = server => {
  emcpItemsAndFluids()
  emcpTags()
  emcpRecipes(server)
}
