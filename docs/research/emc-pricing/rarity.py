"""Rarity prices for GT raw materials (VexedPanda/Mc-incremental#55, re-based in #59).

Usage: python3 rarity.py [ore_counts.json ore_yields.json] > rarity.json

Rarity is how much of a material one Run turns up. A Run lies in one dimension (ADR-0008), so a material's frequency
is the most of it a Run in any one dimension yields: per dimension, every ore block's mean count per Run area
(ore_counts.json) times what fully processing it yields (ore_yields.json: its crushed ores' material unit, the chanced
byproducts of crushing it and those of the better processing route for each crushed ore, ore washer or chemical bath),
plus the chanced byproducts of crushing the dimension's rocks (end stone -> tungstate, netherrack -> gold,
deepslate -> thorium, red granite -> uranium). Rock dusts (stone, deepslate, netherrack, ...) are not materials here:
they are worth their rock (generate.py).

Value scale: a power law in rarity, anchored at iron (a material as common as iron is worth iron's 256):

    value(M) = 256 * (f_iron / f_M) ** EXPONENT

rounded to the nearest power of two (ProjectE's own value scale) and clamped to [MIN_VALUE, MAX_VALUE]. EXPONENT is at
least 1 (owner decision, #59: rarer veins may pay more per Run, so chasing EMC is a real choice between Candidate
areas); it and MAX_VALUE are the dials tuned with prestiges_per_tier.py (5-10 Prestiges per tier). There is no fit to
ProjectE's own metal prices any more: GT-mined metals are priced by rarity.

The better route depends on prices, so the frequencies are found with the washer route, priced, and the routes picked
again by the value of their byproducts until they settle.
"""
import json, math, os, sys

ANCHOR, ANCHOR_VALUE = 'iron', 256
# The dials (RARITY_EXPONENT and RARITY_MAX in the environment override them, for sweeps).
EXPONENT = float(os.environ.get('RARITY_EXPONENT', 1.0))
MIN_VALUE = 16
MAX_VALUE = int(os.environ.get('RARITY_MAX', 16384))  # 2^14, two diamonds; see docs/pocs/poc-1.md

# Rock dusts: worth their rock, never priced by rarity.
ROCKS = {'stone', 'deepslate', 'netherrack', 'endstone', 'andesite', 'diorite', 'granite', 'red_granite', 'marble',
         'basalt', 'blackstone', 'tuff', 'calcite', 'soapstone_rock'}
# Ore blocks GT has no macerator recipe for: what one block yields when mined.
VANILLA_DROPS = {'minecraft:nether_quartz_ore': ('nether_quartz', 1.0)}


def best_route(routes, prices):
    """The processing route whose byproducts are worth more (washer when nothing is priced yet)."""
    if not prices or len(routes) == 1:
        return routes.get('washer') or next(iter(routes.values()), {})
    worth = lambda r: sum(n * prices.get(m, 0) for m, n in routes[r].items() if m not in ROCKS)
    return routes[max(sorted(routes), key=worth)]


def per_dimension(counts, yields, prices=None):
    """{dimension: {material: units per Run}}."""
    ores, crushed, rocks = yields['ores'], yields['crushed'], yields.get('rocks', {})
    out = {}
    for dim, data in counts.items():
        f = {}

        def add(m, n):
            if m not in ROCKS:
                f[m] = f.get(m, 0.0) + n

        for block, mean in data['mean_ore_blocks'].items():
            if block in VANILLA_DROPS:
                m, n = VANILLA_DROPS[block]
                add(m, mean * n)
                continue
            o = ores.get(block)
            if o is None:
                continue
            mat, count, byproducts = o
            (unit, amount), routes = crushed[mat]
            add(unit, mean * count * amount)
            for m, n in byproducts.items():
                add(m, mean * n)
            for m, n in best_route(routes, prices).items():
                add(m, mean * count * n)
        for block, mean in data.get('mean_other_blocks', {}).items():
            if block in rocks:
                for m, n in rocks[block][1].items():
                    add(m, mean * n)
        out[dim] = f
    return out


def frequencies(dims):
    """A material's units per Run in the dimension that yields the most of it, and that dimension."""
    f, where = {}, {}
    for dim, fd in dims.items():
        for m, n in fd.items():
            if n > f.get(m, 0):
                f[m], where[m] = n, dim
    return f, where


def price(f):
    values = {}
    for m, fm in f.items():
        if fm <= 0:
            continue
        raw = ANCHOR_VALUE * (f[ANCHOR] / fm) ** EXPONENT
        v = 2 ** round(math.log2(raw))
        values[m] = int(min(MAX_VALUE, max(MIN_VALUE, v)))
    return values


def solve(counts, yields):
    prices = None
    for _ in range(10):
        dims = per_dimension(counts, yields, prices)
        f, where = frequencies(dims)
        new = price(f)
        if new == prices:
            break
        prices = new
    return dims, f, where, prices


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    cf, yf = argv if len(argv) == 2 else (os.path.join(here, 'ore_counts.json'), os.path.join(here, 'ore_yields.json'))
    dims, f, where, values = solve(json.load(open(cf)), json.load(open(yf)))
    out = {'comment': 'Generated by rarity.py: units per Run in the dimension that yields the most (per_run, '
                      'dimension), per dimension, and EMC value.',
           'exponent': EXPONENT, 'anchor': {ANCHOR: ANCHOR_VALUE}, 'min_value': MIN_VALUE, 'max_value': MAX_VALUE,
           'materials': {m: {'per_run': round(f[m], 3), 'dimension': where[m],
                             'by_dimension': {d: round(dims[d][m], 3) for d in sorted(dims) if dims[d].get(m)},
                             'emc': values[m]} for m in sorted(values)}}
    json.dump(out, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main(sys.argv[1:])
