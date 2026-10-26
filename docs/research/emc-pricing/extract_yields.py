"""Ore processing yields per ore block, from a recipe dump (dump.js `RDUMP` lines in a server log).

Usage: python3 extract_yields.py SERVER_LOG > ore_yields.json

For every ore block and raw ore that a GT macerator recipe crushes, records the crushed ore it gives, how many, and the
expected chanced byproducts. For every crushed ore it records the material unit (dust or gem) GT's standard route
ends in (-> purified ore -> thermal centrifuge -> macerator) and each route's expected byproducts: "washer" (ore washer
with water first) and, where GT has one, "bath" (chemical bath, mercury or sodium persulfate, first). rarity.py and
generate.py take the route whose byproducts are worth more (the owner's "best route", #59). For every rock block in
ore_counts.json that a macerator crushes (stone, deepslate, netherrack, end stone, ...) it records the rock's dust and
the expected chanced byproducts (end stone -> tungstate, netherrack -> gold, deepslate -> thorium). Amounts are in units
of a material's dust or gem (small dust 1/4, tiny dust 1/9, nugget 1/9; chipped/flawed/flawless/exquisite gem 1/4,
1/2, 2, 4) and chances are expected values (chance / max chance). Machine tier chance boosts are ignored.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emcmodel import _lines  # noqa: E402

GEM_SCALE = {'chipped_': 0.25, 'flawed_': 0.5, 'flawless_': 2, 'exquisite_': 4}
VANILLA_UNITS = {'minecraft:redstone': 'redstone', 'minecraft:diamond': 'diamond', 'minecraft:emerald': 'emerald',
                 'minecraft:coal': 'coal', 'minecraft:lapis_lazuli': 'lapis', 'minecraft:quartz': 'nether_quartz',
                 'minecraft:amethyst_shard': 'amethyst', 'minecraft:flint': 'flint', 'minecraft:glowstone_dust': 'glowstone'}

VANILLA_NUGGETS = {'minecraft:gold_nugget': 'gold', 'minecraft:iron_nugget': 'iron'}


def unit(item):
    """(material, amount) for a dust or gem item, else None."""
    if item in VANILLA_UNITS:
        return VANILLA_UNITS[item], 1.0
    if item in VANILLA_NUGGETS:
        return VANILLA_NUGGETS[item], 1 / 9
    if not item.startswith('gtceu:'):
        return None
    name = item[6:]
    for suffix in ('_dust', '_gem'):
        if name.endswith(suffix):
            base, scale = name[:-len(suffix)], 1.0
            for prefix, s in [('small_', 0.25), ('tiny_', 1 / 9)] + list(GEM_SCALE.items()):
                if base.startswith(prefix):
                    base, scale = base[len(prefix):], s
                    break
            if suffix == '_dust' and base.startswith(('impure_', 'pure_')):
                return None
            return base, scale
    return None


def outputs(recipe):
    """Guaranteed and chanced item outputs as (item, expected count, guaranteed)."""
    for o in recipe['o']:
        if len(o['ids']) == 1:
            yield o['ids'][0], o['n'] * o['ch'] / o['mx'], o['ch'] >= o['mx']


def main(log):
    recipes = {}
    for line in _lines(log):
        i = line.find('RDUMP {')
        if i >= 0:
            r = json.loads(line[i + 6:])
            if r.get('gt'):
                recipes[r['id']] = r
    ores, crushed = {}, {}
    for rid, r in recipes.items():
        if not rid.startswith('gtceu:macerator/macerate_') or not rid.endswith('_to_crushed_ore'):
            continue
        outs = list(outputs(r))
        main_out = [(i, n) for i, n, g in outs if g and i.startswith('gtceu:crushed_')]
        if len(main_out) != 1 or len(r['i']) < 1:
            continue
        crushed_item, count = main_out[0]
        byp = {}
        for i, n, g in outs:
            u = unit(i)
            if not g and u:
                byp[u[0]] = round(byp.get(u[0], 0) + n * u[1], 4)
        for ore in r['i'][0]['ids']:
            ores[ore] = [crushed_item[len('gtceu:crushed_'):-len('_ore')], count, byp]
    for mat in sorted({o[0] for o in ores.values()}):
        primary, routes = None, {}
        for name, first in (('washer', 'gtceu:ore_washer/wash_%s_crushed_ore_to_purified_ore' % mat),
                            ('bath', 'gtceu:chemical_bath/bathe_%s_crushed_ore_to_purified_ore' % mat)):
            route = [first, 'gtceu:thermal_centrifuge/centrifuge_%s_purified_ore_to_refined_ore' % mat,
                     'gtceu:macerator/macerate_%s_refined_ore_to_dust' % mat]
            if any(rid not in recipes for rid in route):
                continue
            byp = {}
            for step, rid in enumerate(route):
                for i, n, g in outputs(recipes[rid]):
                    u = unit(i)
                    if not u:
                        continue
                    if g and step == 2:
                        primary = primary or [u[0], n * u[1]]
                    elif not g:
                        byp[u[0]] = round(byp.get(u[0], 0) + n * u[1], 4)
            routes[name] = byp
        crushed[mat] = [primary, routes]
    blocks = set()
    for dim in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ore_counts.json'))).values():
        blocks.update(dim.get('mean_other_blocks', {}))
    rocks = {}
    for rid, r in recipes.items():
        if not rid.startswith('gtceu:macerator/') or len(r['i']) != 1 or len(r['o']) < 2:
            continue
        for rock in r['i'][0]['ids']:
            if rock not in blocks or r['i'][0]['n'] != 1:
                continue
            outs = list(outputs(r))
            dust = [i for i, n, g in outs if g]
            byp = {}
            for i, n, g in outs:
                u = unit(i)
                if not g and u and i not in dust:
                    byp[u[0]] = round(byp.get(u[0], 0) + n * u[1], 4)
            if len(dust) == 1 and byp:
                rocks[rock] = [dust[0], byp]
    # One line per entry keeps the file small and diffable.
    out = ['{"comment": "Generated by extract_yields.py. ores: block -> [crushed ore material, crushed per block, '
           '{byproduct material: expected units}]. crushed: material -> [[unit material, units per crushed ore], '
           '{route (washer, bath): {byproduct material: expected units per crushed ore}}]. rocks: block -> [its dust, '
           '{byproduct material: expected units per block}]",']
    for key, table in (('ores', ores), ('crushed', crushed), ('rocks', rocks)):
        rows = ['  %s: %s' % (json.dumps(k), json.dumps(v, sort_keys=True)) for k, v in sorted(table.items())]
        out.append(' "%s": {\n%s\n }%s' % (key, ',\n'.join(rows), '' if key == 'rocks' else ','))
    sys.stdout.write('\n'.join(out) + '\n}\n')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
