"""Automatable loops: GT recipes whose outputs are worth more than their inputs (VexedPanda/Mc-incremental#55, #59).

Usage: python3 audit.py [DUMP] [RATIO] [MIN_RATE] [--model GEN_OUT.json] > audit.txt

ProjectE's own exploit scan only sees the conversions it maps. This replays every GT machine recipe against the
in-game values in a dump (dump.js; by default the committed dump.txt.xz): consumed inputs (chanced ones at their
chance) against every output (chanced ones at their expected amount), items at their EMC and fluids at their fluid_emc
value per 1000 mB (water and other free fluids 0). The check is ratio-based (owner decision 6, #59): a recipe is an
exploit when its outputs are worth more than RATIO (default 1.1) times its inputs and, at machine speed (the recipe's
duration in the dump, no overclocking), one machine gains at least MIN_RATE (default 5) EMC per second. Below that a
machine makes under 18,000 EMC an hour, about 0.03% of what one Run yields (prestiges_per_tier.txt): rounding (tiny
dusts, planks, 1-EMC stone) and leaks too small to matter.

Four kinds are listed apart:
- recipes with no consumed input (rock breaker, gas collector, air scrubber): free resources ADR-0005 allows when their
  EMC is low; their EMC per second is what one machine makes;
- recipes making a material with a late-tier floor (hand_values.json "floors"): their gain is intended (owner
  decision 3), at the floor's tier;
- recipes gaining under 10 EMC per run: rounding (ProjectE's values are whole EMC; a tiny dust can't be worth less
  than 1);
- every other gaining recipe: the exploits pricing should fix. The count of those gaining 100+ EMC per run (the
  earlier fixed threshold) is printed too.

Invariants (the dump's values): each GT material's dust and ingot within rounding; free fluids above 1.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from emcmodel import load_dump  # noqa: E402

TIERS = ['ULV', 'LV', 'MV', 'HV', 'EV', 'IV', 'LuV', 'ZPM', 'UV', 'UHV', 'UEV', 'UIV', 'UXV', 'OpV', 'MAX']


def main(argv):
    model = argv[argv.index('--model') + 1] if '--model' in argv else None
    args = [a for a in argv if not a.startswith('--') and a != model]
    log = args[0] if args else os.path.join(HERE, 'dump.txt.xz')
    ratio = float(args[1]) if len(args) > 1 else 1.1
    min_rate = float(args[2]) if len(args) > 2 else 5
    items, fluids, _, recipes = load_dump(log)
    if model:  # a generate.py GEN_OUT: the values it would write, against the dump's recipes
        g = json.load(open(model))
        items = {k: int(g['val'].get('i:' + k, 0)) for k in items}
        fluids = {f: (v[0], g['listed'].get(v[0], 0), v[2]) for f, v in fluids.items()}
    hand = json.load(open(os.path.join(HERE, 'hand_values.json')))
    floored = sorted(hand.get('floors', {}).get('materials', {}))
    floor_rx = re.compile(r'^gtceu:(hot_|tiny_|small_)?(%s)(_dust|_ingot|_nugget|_block|_gem|_plate|_plasma)?$' % '|'.join(floored))
    fval = {f: v[1] for f, v in fluids.items()}
    free, floor_rows, rows, rounding = [], [], [], []
    for r in recipes:
        if not r.get('gt'):
            continue
        cost = gain = 0.0
        ok = True
        consumed = False
        for x in r['i']:
            if x['ch'] == 0:
                continue
            vs = [items.get(i, 0) for i in x['ids'] if items.get(i, 0) > 0]
            if not vs:
                ok = False
                break
            consumed = True
            cost += min(vs) * x['n'] * x['ch'] / x['mx']
        for x in r['fi']:
            if x['ch'] > 0 and x['ids']:
                v = min(fval.get(i, 0) for i in x['ids'])
                consumed |= v > 0
                cost += v * x['n'] / 1000
        if not ok:
            continue
        outs = []
        for x in r['o']:
            if len(x['ids']) == 1:
                gain += items.get(x['ids'][0], 0) * x['n'] * x['ch'] / x['mx']
                outs.append(x['ids'][0])
        for x in r['fo']:
            if len(x['ids']) == 1:
                gain += fval.get(x['ids'][0], 0) * x['n'] / 1000 * x['ch'] / x['mx']
                outs.append(x['ids'][0])
        secs = max(1, r.get('d') or 1) / 20
        tier = TIERS[r['t']] if isinstance(r.get('t'), int) and 0 <= r['t'] < len(TIERS) else '?'
        row = (gain - cost, cost, gain, (gain - cost) / secs, tier, r['id'])
        if not consumed:
            if row[3] >= min_rate:
                free.append(row)
            continue
        if gain <= ratio * cost or row[3] < min_rate or gain - cost < 2:
            continue
        if floored and any(floor_rx.match(o) for o in outs):
            floor_rows.append(row)
        elif gain - cost < 10:
            rounding.append(row)
        else:
            rows.append(row)

    def table(title, rs):
        print('## %s: %d' % (title, len(rs)))
        print()
        if rs:
            print('| Gain/run | Inputs | Outputs | Ratio | EMC/s | Tier | Recipe |')
            print('|---:|---:|---:|---:|---:|---|---|')
            for d, c, g, ps, t, rid in sorted(rs, reverse=True):
                print('| %s | %s | %s | %s | %s | %s | %s |' % ('{:,.0f}'.format(d), '{:,.0f}'.format(c), '{:,.0f}'.format(g),
                      ('%.2f' % (g / c)) if c else '-', '{:,.1f}'.format(ps), t, rid))
            print()

    print('# GT recipe audit (#59), from %s: outputs > %g x inputs, gaining %g+ EMC per second at machine speed' % (
        os.path.basename(log), ratio, min_rate))
    print()
    table('Exploits (gaining recipes pricing should fix)', rows)
    print('Of those, gaining 100+ EMC per run: %d' % sum(1 for r in rows if r[0] >= 100))
    print()
    table('Recipes making a floored late-tier material (intended, owner decision 3)', floor_rows)
    table('Recipes with no consumed input (free resources, ADR-0005)', free)
    table('Rounding: gaining under 10 EMC per run (ProjectE values whole EMC, so a dust worth a few EMC unpacks into '
          'tiny dusts worth 1 each)', rounding)
    # invariants
    print('## Invariants')
    print()
    bad = []
    for item, v in sorted(items.items()):
        if item.startswith('gtceu:') and item.endswith('_ingot') and not item.startswith('gtceu:hot_'):
            d = items.get(item[:-6] + '_dust')
            if d is not None and v and abs(v - d) > max(1, 0.01 * v):
                bad.append('%s %d vs dust %d' % (item, v, d))
    print('- dust = ingot (within 1 EMC or 1%%): %s' % ('holds' if not bad else '%d differ: %s' % (len(bad), ', '.join(bad))))
    low = [f for f in ('gtceu:air', 'gtceu:nether_air', 'gtceu:ender_air', 'gtceu:oxygen', 'gtceu:hydrogen',
                       'gtceu:nitrogen') if not fval.get(f, 0) > 1]
    print('- free fluids above 1 EMC per 1000 mB: %s' % ('holds' if not low else 'fails for ' + ', '.join(low)))


if __name__ == '__main__':
    main(sys.argv[1:])
