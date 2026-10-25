# No free resource generation beyond low-EMC renewables

Resources must come from the Run area itself. Resource scarcity is what forces a Prestige, so nothing in the Pack may create meaningful value from nothing. The line is drawn by **EMC yield, not by resource type**: because EMC converts anything into anything, a farm of iron is no different from a farm of wheat if both yield the same EMC. Ordinary game mechanics stay (infinite water, crops, animal breeding, tree farms, mob drops, villager trades, loot chests) as long as what they produce has low EMC value. Large farms are also self-limiting: a Prestige leaves them behind.

So ProjectE's Energy Collectors and power flowers are disabled, Monifactory-style resource creation (microverses, void miners) is out, and EMC values are the balancing tool. The Pack uses ProjectE's default EMC values wherever ProjectE has one (renewables such as iron and gold keep their default values); what gets fixed is any loop that lets a player create or duplicate roughly 100+ EMC in an automatable way.

## Consequences

- Every new mod needs an audit for high-value free generation (void miners, infinite fluid wells, rock breakers yielding ores, ore-producing generators).
- EMC values are a core balance surface, not a detail: a renewable output with a high EMC value breaks the loop.
- To keep the PoC simple (#47), the Pack uses ProjectE's default EMC values wherever ProjectE has one, rather than lowering the values of renewables such as iron and gold. Renewables and conversions are judged by the exploit threshold instead: a loop that lets a player create or duplicate roughly 100+ EMC in an automatable way gets fixed, each one decided individually; smaller free-EMC leaks are accepted. Hand-set values are only for what ProjectE can't value (GT parts, machines and materials) and for fluids.
- Fluids that are real fuels or resources keep an explicit EMC value; water is free. Lava uses ProjectE's default (64 EMC per bucket), low enough that ProjectE's Volcanite Amulet (lava from EMC fuel, not automatable) stays.
- Villager trades are welcome as a way to discover resources missing from the Run area (issue #12); an exploitable trade gets fixed individually.
- Monifactory remains a reference for recipe and progression design only.
