// Hide the uncraftable free-resource machines in EMI (ADR-0005, issue #40).
// Client-side because KubeJS's EMI plugin only reads server-sent viewer data on
// an EMI reload. The list lives in startup_scripts/free_resource_items.js.
RecipeViewerEvents.removeEntriesCompletely('item', event => {
  global.FREE_RESOURCE_ITEMS.forEach(item => event.remove(item))
})
