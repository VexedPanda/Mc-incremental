"""EU price from generation cost, and the pump check (VexedPanda/Mc-incremental#64; ../energy-in-emc.md).

Usage: python3 eu_price.py [--model GEN_OUT.json] [--hours H[,H...]] [--price P] > eu_price.txt
       python3 eu_price.py [--model GEN_OUT.json] --rate R|'{"LV": R, ...}'   (time-priced EU, ../time-in-emc.md)

Every steady way to make EU in the Pack, with what one generator makes per second and what it burns:

    EMC per EU (generator g, horizon H) = (fuel EMC per second + generator EMC / H) / EU per second

The time term charges the generator's own EMC (the time cost the owner asked for) over H hours of running; H is the
dial. The EU price at a tier is the cheapest generator available by that tier. Fuel and generator values come from the
dump (or a generate.py GEN_OUT model, so a second pass sees fuels that themselves include energy); EU from eu.txt.xz
(dump_eu.js), steam per fuel from GT 8.0's boiler code (gtceu.yaml defaults):

- small boilers make base/20 mB of steam per tick at full heat (LP solid 120/s, HP solid 300/s, LP liquid 240/s, HP
  liquid 600/s, LP solar 120/s, HP solar 360/s); a solid fuel lasts its furnace burn time (HP boilers: half), a liquid
  its steam_boiler recipe's duration (HP: half); solar boilers and solar panel covers work in daylight (DAYLIGHT);
- large boilers make (max temperature) mB of steam per tick (bronze 800, steel 1,800, titanium 3,200, tungstensteel
  6,400; steamPerWater 160 at full throttle); a solid fuel lasts burn time / 4, a liquid its large_boiler recipe's
  duration, whatever the boiler's tier (LargeBoilerLogic.modifyBurnTime, LargeBoilerMachine.recipeModifier = IDENTITY);
- steam turbines turn 2 mB of steam into 1 EU (steam_turbine/steam: 640 mB, 10 t at 32 EU/t); steam is costed at the
  boiler's fuel, and every steam setup pays for the LV steam turbines it needs (64 mB/t each);
- combustion generators, gas turbines and plasma generators: their recipes (EU = output voltage x amperage x
  duration, at the LV or EV machine; higher tiers are not more efficient);
- solar panel covers: V[tier] EU/t in daylight (CoverSolarPanel).

The pump check: at price p, generator g makes (EU/s x p - fuel EMC/s) EMC per second when its EU goes into recipes
whose outputs carry it. With p the cheapest generator's full cost, that is at most g's own time term (generator EMC /
H) for every g, and never more than the fuel for a horizon of 'infinite' (p = cheapest fuel cost).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from emcmodel import TIER_NAMES, load_dump, load_eu  # noqa: E402

DAYLIGHT = 0.5  # share of the day a solar boiler or panel works
TIERS = ['LV', 'MV', 'HV', 'EV', 'IV', 'LuV', 'ZPM', 'UV']
# Furnace burn times (ticks) of the solid fuels worth checking (vanilla and GT values).
BURN = {'minecraft:coal': 1600, 'minecraft:charcoal': 1600, 'minecraft:coal_block': 16000, 'minecraft:oak_log': 300,
        'minecraft:oak_planks': 300, 'minecraft:stick': 100, 'minecraft:blaze_rod': 2400,
        'minecraft:dried_kelp_block': 4000, 'minecraft:bamboo': 50, 'gtceu:coke_gem': 3200, 'gtceu:coke_block': 32000,
        'gtceu:charcoal_dust': 1600, 'gtceu:coal_dust': 1600}
STEAM_TURBINE = ('gtceu:lv_steam_turbine', 64)  # item, mB of steam per tick it takes (2 mB per EU, 32 EU/t)
# Small boilers: (item, tier, steam mB per tick, burn time multiplier, kind)
SMALL_BOILERS = [('gtceu:lp_steam_solid_boiler', 'LV', 6, 1, 'solid'), ('gtceu:hp_steam_solid_boiler', 'LV', 15, 0.5, 'solid'),
                 ('gtceu:lp_steam_liquid_boiler', 'LV', 12, 1, 'liquid'), ('gtceu:hp_steam_liquid_boiler', 'LV', 30, 0.5, 'liquid'),
                 ('gtceu:lp_steam_solar_boiler', 'LV', 6, 0, 'solar'), ('gtceu:hp_steam_solar_boiler', 'LV', 18, 0, 'solar')]
# Large boilers: (name, tier, steam mB per tick, {part: count}) (parts from GT's pattern: 3x3 firebox, pipe column, casings)
LARGE_BOILERS = [
    ('bronze', 'LV', 800, {'gtceu:bronze_large_boiler': 1, 'gtceu:bronze_firebox_casing': 9, 'gtceu:bronze_pipe_casing': 3,
                           'gtceu:bronze_brick_casing': 12}),
    ('steel', 'MV', 1800, {'gtceu:steel_large_boiler': 1, 'gtceu:steel_firebox_casing': 9, 'gtceu:steel_pipe_casing': 3,
                           'gtceu:solid_machine_casing': 12}),
    ('titanium', 'EV', 3200, {'gtceu:titanium_large_boiler': 1, 'gtceu:titanium_firebox_casing': 9}),
    ('tungstensteel', 'IV', 6400, {'gtceu:tungstensteel_large_boiler': 1, 'gtceu:tungstensteel_firebox_casing': 9}),
]
# Recipe generators: recipe type -> (machine item, tier it is available from)
RECIPE_GENERATORS = {'gtceu:combustion_generator': ('gtceu:lv_combustion', 'LV'), 'gtceu:gas_turbine': ('gtceu:lv_gas_turbine', 'LV'),
                     'gtceu:plasma_generator': ('gtceu:plasma_large_turbine', 'LuV')}
# Fuels a player can't get: raw oil and light oil only come from the removed Fluid Drilling Rig (ADR-0005, poc-1.md).
UNOBTAINABLE = {'gtceu:raw_oil', 'gtceu:light_oil'}
SOLAR_PANELS = [('gtceu:ulv_solar_panel', 'LV', 8), ('gtceu:lv_solar_panel', 'LV', 32)]


def load(argv):
    items, fluids, _, recipes = load_dump(os.path.join(HERE, 'dump.txt.xz'))
    fval = {f: v[1] for f, v in fluids.items()}
    src = 'dump'
    if '--model' in argv:
        path = argv[argv.index('--model') + 1]
        g = json.load(open(path))
        items = {k: g['val'].get('i:' + k, 0) for k in items}
        fval = {f: g['listed'].get(v[0], g['val'].get('f:' + v[0], 0)) for f, v in fluids.items()}
        src = 'model ' + os.path.basename(path)
    return items, fval, recipes, src


def generators(items, fval, recipes, eu):
    """[(name, tier, EU/s, fuel EMC/s, capital EMC)] for every generator and fuel."""
    out = []
    turbine_cap = items.get(STEAM_TURBINE[0], 0) / STEAM_TURBINE[1]  # EMC per mB/t of steam turned into EU

    def steam(name, tier, mbt, fuel_per_s, cap, solar=False):
        f = DAYLIGHT if solar else 1
        out.append((name, tier, mbt / 2 * 20 * f, fuel_per_s * f, cap + mbt * turbine_cap))

    by_type = {}
    for r in recipes:
        if r.get('gt'):
            by_type.setdefault(r['type'], []).append(r)
    for item, tier, mbt, mult, kind in SMALL_BOILERS:
        cap = items.get(item, 0)
        b = item.split(':')[1]
        if kind == 'solid':
            for fuel, t in BURN.items():
                ticks = t * mult
                steam('%s, %s' % (b, fuel), tier, mbt, items.get(fuel, 0) / ticks * 20, cap)
        elif kind == 'liquid':
            for r in by_type.get('gtceu:steam_boiler', []):
                x = r['fi'][0]
                ticks = r['d'] * mult
                steam('%s, %s' % (b, x['ids'][0]), tier, mbt, fval.get(x['ids'][0], 0) * x['n'] / 1000 / ticks * 20, cap)
        else:
            steam(b, tier, mbt, 0, cap, solar=True)
    for name, tier, mbt, parts in LARGE_BOILERS:
        cap = sum(items.get(p, 0) * n for p, n in parts.items())
        for fuel, t in BURN.items():
            steam('large %s boiler, %s' % (name, fuel), tier, mbt, items.get(fuel, 0) / (t / 4) * 20, cap)
        for r in by_type.get('gtceu:large_boiler', []):
            x = r['fi'][0]
            steam('large %s boiler, %s' % (name, x['ids'][0]), tier, mbt, fval.get(x['ids'][0], 0) * x['n'] / 1000 / r['d'] * 20, cap)
    for rtype, (machine, tier) in RECIPE_GENERATORS.items():
        for r in by_type.get(rtype, []):
            made = eu.get(r['id'], (0, 0, None))[1]
            if not made or not r['fi'] or r['fi'][0]['ids'][0] in UNOBTAINABLE:
                continue
            x = r['fi'][0]
            back = sum(fval.get(o['ids'][0], 0) * o['n'] / 1000 for o in r['fo'])  # plasma comes back as gas
            per_s = 20 / r['d']
            out.append(('%s, %s' % (rtype.split(':')[1], x['ids'][0]), tier, made * per_s,
                        (fval.get(x['ids'][0], 0) * x['n'] / 1000 - back) * per_s, items.get(machine, 0)))
    for item, tier, v in SOLAR_PANELS:
        out.append((item.split(':')[1] + ' cover', tier, v * 20 * DAYLIGHT, 0, items.get(item, 0)))
    return [g for g in out if g[2] > 0]


# ---- time-priced generation (#64, ../time-in-emc.md) ----
# Every generator setup as (name, tier it is available from, EU/s, fuel EMC/s, {time tier: machines}); the time
# term is each machine's running time at R of its tier: price = (fuel EMC/s + sum machines x R[tier]) / EU/s.
V = {'ULV': 8, 'LV': 32, 'MV': 128, 'HV': 512, 'EV': 2048, 'IV': 8192, 'LuV': 32768, 'ZPM': 131072, 'UV': 524288}
ALL_TIERS = ['ULV'] + TIERS
# Single-block generators come in LV, MV and HV (V[tier] EU/t, same fuel per EU); recipe generators' recipes are
# at LV. Large turbines make 2 x V[tier] EU/t with a 100% rotor (LargeTurbineMachine.BASE_EU_OUTPUT; better rotors
# raise it), large combustion engines V[tier] (no oxygen boost); tiers from GTMultiMachines.
SINGLE = {'gtceu:combustion_generator': 'combustion', 'gtceu:gas_turbine': 'gas_turbine'}
LARGE = {'gtceu:combustion_generator': [('large combustion engine', 'EV', 2048, 'EV'),
                                        ('extreme combustion engine', 'IV', 8192, 'IV')],
         'gtceu:gas_turbine': [('large gas turbine', 'EV', 4096 * 2, 'EV')],
         'gtceu:plasma_generator': [('large plasma turbine', 'LuV', 8192 * 2 * 2, 'IV')]}  # plasma needs LuV fusion
LARGE_STEAM_TURBINE = ('HV', 1024 * 2)  # 2 x V[HV] EU/t, from 2 mB of steam per EU: mB of steam per tick it takes


def timed_generators(items, fval, recipes, eu):
    out = []
    by_type = {}
    for r in recipes:
        if r.get('gt'):
            by_type.setdefault(r['type'], []).append(r)

    def steam(name, tier, mbt, fuel_per_s, machines, solar=False):
        f = DAYLIGHT if solar else 1
        eus = mbt / 2 * 20 * f
        # turn the steam into EU with LV steam turbines (64 mB/t each), or from HV with large steam turbines
        out.append((name + ' + LV steam turbines', tier, eus, fuel_per_s * f, dict(machines, LV=machines.get('LV', 0) + mbt / 64)))
        if mbt >= 400:
            t2 = TIERS[max(TIERS.index(tier), TIERS.index('HV'))]
            out.append((name + ' + large steam turbines', t2, eus, fuel_per_s * f,
                        dict(machines, HV=machines.get('HV', 0) + mbt / LARGE_STEAM_TURBINE[1])))

    for item, tier, mbt, mult, kind in SMALL_BOILERS:
        b = item.split(':')[1]
        if kind == 'solid':
            for fuel, t in BURN.items():
                steam('%s, %s' % (b, fuel), tier, mbt, items.get(fuel, 0) / (t * mult) * 20, {'ULV': 1})
        elif kind == 'liquid':
            for r in by_type.get('gtceu:steam_boiler', []):
                x = r['fi'][0]
                steam('%s, %s' % (b, x['ids'][0]), tier, mbt, fval.get(x['ids'][0], 0) * x['n'] / 1000 / (r['d'] * mult) * 20, {'ULV': 1})
        else:
            steam(b, tier, mbt, 0, {'ULV': 1}, solar=True)
    for name, tier, mbt, parts in LARGE_BOILERS:
        for fuel, t in BURN.items():
            steam('large %s boiler, %s' % (name, fuel), tier, mbt, items.get(fuel, 0) / (t / 4) * 20, {tier: 1})
        for r in by_type.get('gtceu:large_boiler', []):
            x = r['fi'][0]
            steam('large %s boiler, %s' % (name, x['ids'][0]), tier, mbt, fval.get(x['ids'][0], 0) * x['n'] / 1000 / r['d'] * 20, {tier: 1})
    for rtype in RECIPE_GENERATORS:
        for r in by_type.get(rtype, []):
            made = eu.get(r['id'], (0, 0, None))[1]
            if not made or not r['fi'] or r['fi'][0]['ids'][0] in UNOBTAINABLE:
                continue
            x = r['fi'][0]
            back = sum(fval.get(o['ids'][0], 0) * o['n'] / 1000 for o in r['fo'])
            fuel_per_eu = (fval.get(x['ids'][0], 0) * x['n'] / 1000 - back) / made
            eut = made / r['d']
            f = x['ids'][0]
            if rtype in SINGLE:
                for t in ('LV', 'MV', 'HV'):
                    eus = eut * V[t] / 32 * 20
                    out.append(('%s %s, %s' % (t, SINGLE[rtype], f), t, eus, eus * fuel_per_eu, {t: 1}))
            for name, avail, eut2, tt in LARGE.get(rtype, []):
                eus = eut2 * 20
                out.append(('%s, %s' % (name, f), avail, eus, eus * fuel_per_eu, {tt: 1}))
    for name, tier, ttier, v in [('ULV solar panel cover', 'LV', 'ULV', 8), ('LV solar panel cover', 'LV', 'LV', 32)]:
        out.append((name, tier, v * 20 * DAYLIGHT, 0, {ttier: 1}))
    return [g for g in out if g[2] > 0 and g[3] >= 0]


def time_price(g, rates):
    """EMC per EU of generator g at R = rates {tier name: EMC per machine-second}."""
    return (g[3] + sum(n * rates.get(t, 0) for t, n in g[4].items())) / g[2]


def time_cheapest(gens, tier, rates):
    ok = [g for g in gens if TIERS.index(g[1]) <= TIERS.index(tier)]
    return min(ok, key=lambda g: time_price(g, rates))


def price(g, hours):
    return (g[3] + (g[4] / (hours * 3600) if hours else 0)) / g[2]


def cheapest(gens, tier, hours):
    ok = [g for g in gens if TIERS.index(g[1]) <= TIERS.index(tier) and g[4] > 0]  # unvalued machines can't be costed
    return min(ok, key=lambda g: price(g, hours))


def main_rate(argv, items, fval, recipes, eu, src):
    rates = json.loads(argv[argv.index('--rate') + 1])
    if not isinstance(rates, dict):
        rates = {t: rates for t in ALL_TIERS}
    gens = timed_generators(items, fval, recipes, eu)
    print('# EU price with time counted (#64), R = %s, values from %s' % (rates, src))
    print()
    print('| Tier | EMC/EU | Set by | Fuel EMC/s | Time EMC/s | EU/s |')
    print('|---|---:|---|---:|---:|---:|')
    for t in TIERS:
        g = time_cheapest(gens, t, rates)
        print('| %s | %.3g | %s | %.2f | %.2f | %s |' % (t, time_price(g, rates), g[0], g[3],
              sum(n * rates.get(k, 0) for k, n in g[4].items()), '{:,.0f}'.format(g[2])))


def main(argv):
    items, fval, recipes, src = load(argv)
    eu = load_eu()
    if '--rate' in argv:
        return main_rate(argv, items, fval, recipes, eu, src)
    hours = [float(h) if h != 'inf' else None for h in
             (argv[argv.index('--hours') + 1] if '--hours' in argv else 'inf,100,10,1').split(',')]
    gens = generators(items, fval, recipes, eu)
    print('# EU price from generation cost (#64), values from %s' % src)
    print()
    print('Each generator with its fuel: EU per second, fuel EMC per second, generator EMC (with the LV steam turbines '
          'a boiler needs), and EMC per EU for the fuel alone and with the generator amortised over H hours.')
    print()
    print('| Generator, fuel | From | EU/s | Fuel EMC/s | Generator EMC | %s |' % ' | '.join(
        'EMC/EU (fuel only)' if h is None else 'EMC/EU (H = %g h)' % h for h in hours))
    print('|---|---|---:|---:|---:|%s' % ('---:|' * len(hours)))
    for g in sorted(gens, key=lambda g: price(g, hours[0])):
        print('| %s | %s | %s | %s | %s | %s |' % (g[0], g[1], '{:,.0f}'.format(g[2]), '{:,.2f}'.format(g[3]),
              '{:,.0f}'.format(g[4]), ' | '.join('%.3g' % price(g, h) for h in hours)))
    print()
    print('## Cheapest generation by tier (the derived EU price)')
    print()
    print('| Tier | %s |' % ' | '.join('fuel only' if h is None else 'H = %g h' % h for h in hours))
    print('|---|%s' % ('---|' * len(hours)))
    derived = {}
    for t in TIERS:
        cells = []
        for h in hours:
            g = cheapest(gens, t, h)
            derived.setdefault(h, {})[t] = price(g, h)
            cells.append('%.3g (%s)' % (price(g, h), g[0]))
        print('| %s | %s |' % (t, ' | '.join(cells)))
    print()
    print('EMC_EU_PRICE for each horizon: ' + '; '.join('%s: %s' % ('fuel only' if h is None else 'H=%g h' % h, json.dumps(
        {t: float('%.3g' % p) for t, p in d.items()})) for h, d in derived.items()))
    prices = [float(p) for p in argv[argv.index('--price') + 1].split(',')] if '--price' in argv else []
    prices += sorted({derived[h]['LV'] for h in hours})
    print()
    print('## Pump check: EMC per second each generator makes at a flat price p (EU/s x p - fuel EMC/s)')
    print()
    print('Positive means burning that fuel and banking the EU in recipe outputs makes EMC. The worst five per price:')
    print()
    for p in prices:
        worst = sorted(gens, key=lambda g: g[3] - g[2] * p)[:5]
        print('- p = %.3g EMC/EU: %s' % (p, '; '.join('%s %+.1f EMC/s (%+.0f per hour)' % (
            g[0], g[2] * p - g[3], (g[2] * p - g[3]) * 3600) for g in worst)))


if __name__ == '__main__':
    main(sys.argv[1:])
