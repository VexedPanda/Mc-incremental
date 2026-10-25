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
  }
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
