"""Automatable loops ProjectE's exploit scan can't see (VexedPanda/Mc-incremental#55).

Usage: python3 audit.py [SERVER_LOG] [THRESHOLD]

ProjectE only checks conversions it maps, and the GT recipe mapper (#52) leaves out decompositions, recycling and
every output but the first. This replays every GT machine recipe against the in-game values in a dump (dump.js) and
lists those whose outputs, chanced ones at their expected amount, are worth THRESHOLD (default 100) or more EMC above
their consumed inputs. Fluids are valued per their fluid_emc value (FLUIDDUMP); water and other free fluids at 0.
"""
import os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from emcmodel import load_dump  # noqa: E402


def main(argv):
    log = argv[0] if argv else os.path.join(HERE, 'dump.txt.xz')
    threshold = float(argv[1]) if len(argv) > 1 else 100
    items, fluids, _, recipes = load_dump(log)
    fval = {f: v[1] for f, v in fluids.items()}
    rows = []
    for r in recipes:
        if not r.get('gt'):
            continue
        cost = gain = 0.0
        ok = True
        for x in r['i']:
            if x['ch'] == 0 or x.get('cu') == 'IntCircuitIngredient':
                continue
            vs = [items.get(i, 0) for i in x['ids'] if items.get(i, 0) > 0]
            if not vs:
                ok = False
                break
            cost += min(vs) * x['n'] * x['ch'] / x['mx']
        for x in r['fi']:
            if x['ch'] > 0 and x['ids']:
                cost += min(fval.get(i, 0) for i in x['ids']) * x['n'] / 1000
        if not ok:
            continue
        for x in r['o']:
            if len(x['ids']) == 1:
                gain += items.get(x['ids'][0], 0) * x['n'] * x['ch'] / x['mx']
        for x in r['fo']:
            if len(x['ids']) == 1:
                gain += fval.get(x['ids'][0], 0) * x['n'] / 1000 * x['ch'] / x['mx']
        if gain - cost >= threshold:
            rows.append((gain - cost, cost, gain, r['id']))
    for d, c, g, rid in sorted(rows, reverse=True):
        print('%10.0f  cost %10.0f  outputs %10.0f  %s' % (d, c, g, rid))
    print('%d GT recipes gain %g EMC or more per run' % (len(rows), threshold))


if __name__ == '__main__':
    main(sys.argv[1:])
