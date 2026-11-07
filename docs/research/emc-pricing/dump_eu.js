// EU dump for the energy-in-EMC research (VexedPanda/Mc-incremental#64; docs/research/energy-in-emc.md). NOT part of
// the Pack.
//
// Append to a copy of pack/kubejs/server_scripts/smoke_test.js in a smoke-test server's work dir (as with dump.js)
// and call `emcEuDump(server)` at the start of its runAssertions. It logs, for every GT recipe:
//   EUDUMP {"id":..., "d": duration ticks, "iv"/"ia": per-tick EU input voltage and amperage,
//           "ov"/"oa": per-tick EU output (generators), "start": fusion eu_to_start or null}
// EU per run = voltage x amperage x duration. GT 8.0's API: GTRecipe.getInputEUt() / getOutputEUt() return an
// EnergyStack(voltage, amperage); GTRecipe.duration; the fusion start energy is GTRecipe.data's "eu_to_start".
// It relies on the smoke test's smokeRegistries and smokeGTRecipe.
const emcEuDump = server => {
  let it = server.recipeManager.getRecipes().iterator()
  while (it.hasNext()) {
    let holder = it.next()
    let r = holder.value()
    if (!(r instanceof smokeGTRecipe)) continue
    let o = { id: String(holder.id()), d: r.duration }
    try {
      let i = r.getInputEUt(); o.iv = Number(i.voltage()); o.ia = Number(i.amperage())
      let u = r.getOutputEUt(); o.ov = Number(u.voltage()); o.oa = Number(u.amperage())
      o.start = r.data != null && r.data.contains('eu_to_start') ? Number(r.data.getLong('eu_to_start')) : null
    } catch (e) { o.err = String(e) }
    console.info('EUDUMP ' + JSON.stringify(o))
  }
  console.info('EUDUMP-END')
}
