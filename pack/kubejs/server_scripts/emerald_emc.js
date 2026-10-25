// Emerald EMC (issue #53).
//
// Villagers buy an emerald for items worth almost nothing, so the emerald is
// pinned low (config/ProjectE/custom_emc.json, tag c:gems/emerald) and a trade
// gains less than ADR-0005's 100 EMC threshold. See docs/pocs/poc-1.md.
//
// ProjectE's Philosopher's Stone emerald conversions assume its default ratio
// (1 emerald = 2 diamonds = 16,384 EMC). At the pinned value, emerald_to_diamond
// turns a 64 EMC emerald into 16,384 EMC of diamonds, and diamond_to_emerald
// throws away 16,320 EMC, so both are removed. Transmutation still converts
// between them at the real values.

ServerEvents.recipes(event => {
  ;['emerald_to_diamond', 'diamond_to_emerald'].forEach(id => event.remove({ id: 'projecte:conversions/' + id }))
})
