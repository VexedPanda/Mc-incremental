"""Time in EMC: sweep schedules of R, the EMC per machine-second (VexedPanda/Mc-incremental#64; ../time-in-emc.md).

Usage: python3 time_sweep.py [OUT_DIR] > time_sweep.txt

Owner decision (#64): every GT recipe's value = material inputs + EU x the EU price + duration x R at the recipe's
tier, and the EU price at a tier = min over the generators available by that tier of (fuel EMC + generator time x R)
/ EU made (eu_price.timed_generators; solar's fuel is 0). A loop is an exploit only when it gains more than its
machine's time.

For each schedule (SCHEDULES) it:
1. derives the EU price per tier and the generator that sets it, from the dump's values (pass 1) and again from the
   model's (pass 2: fuels now carry their own time);
2. replays the committed audit.txt's in-game exploits, each paying its EU and its time (first order: in-game values
   otherwise unchanged): what stays open by #63 group, and the worst gain per second above the time cost;
3. runs generate.py (EMC_EU_PRICE and EMC_TIME_RATE set) with #59's floors, with them halved and without them, then
   audit.py and prestiges_per_tier.py against each model;
4. reports what a base earns per hour from time (BASE_MACHINES machines at the tier and the generators powering
   them, at full uptime with every output banked), against EMC per Run;
5. checks pumps: the step-down pump (a tier's recipe run on the cheapest EU), overclocking (a recipe run faster in a
   higher-tier machine), and crafting-table recipes ProjectE doesn't map (GT tools) that now undercut a GT route.
"""
import json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eu_price  # noqa: E402
from emcmodel import TIER_NAMES, load_dump, load_eu  # noqa: E402
from energy_sweep import GROUPS, group, in_game_rows, prestiges, sections  # noqa: E402

TIERS = ['ULV', 'LV', 'MV', 'HV', 'EV', 'IV', 'LuV', 'ZPM', 'UV']
V = {t: 8 * 4 ** i for i, t in enumerate(TIERS)}


def geometric(lv, factor):
    return {t: lv * factor ** (i - 1) for i, t in enumerate(TIERS)}


# The Prestige-derived schedule: 'LV 1 x4' to EV, then the R from IV up that brings the late tiers' Prestiges into
# 5-10 without floors while still rising at least x2 per tier (the overclocking check): tuned by hand over IV R of
# 2,048-16,384 (../time-in-emc.md). IV itself stays at 4.5: its kit is mostly lower-tier time.
DERIVED = dict(geometric(1, 4), IV=2048, LuV=4096, ZPM=8192, UV=16384)
SCHEDULES = [
    ('LV 4 x4', geometric(4, 4)),
    ('LV 4 x2', geometric(4, 2)),
    ('LV 1 x4', geometric(1, 4)),
    ('flat 4', {t: 4 for t in TIERS}),
    ('Prestige-derived', DERIVED),
]
BASE_MACHINES = 10
# Net EMC per Run while working towards each tier (prestiges_per_tier.txt; mining income, unchanged by time)
RUN_NET = {'LV': 6646510, 'MV': 9900016, 'HV': 32674560, 'EV': 65209623, 'IV': 65209623, 'LUV': 65209623,
           'ZPM': 65209623, 'UV': 65209623}
FLOOR_VARIANTS = [('floors', None), ('half floors', 0.5), ('no floors', 0.0)]


def eu_schedule(rates, values=None):
    """({tier: EMC per EU}, {tier: generator name}) at R = rates."""
    if values is None:
        items, fval, recipes, _ = eu_price.load([])
    else:
        items, fval, recipes, _ = eu_price.load(['--model', values])
    gens = eu_price.timed_generators(items, fval, recipes, load_eu())
    prices, who, gen = {}, {}, {}
    for t in TIERS[1:]:
        g = eu_price.time_cheapest(gens, t, rates)
        prices[t], who[t], gen[t] = eu_price.time_price(g, rates), g[0], g
    prices['ULV'], who['ULV'], gen['ULV'] = prices['LV'], who['LV'], gen['LV']
    return prices, who, gen


def run(job, out_dir):
    name, rates, prices, fname, fscale = job
    tag = re.sub(r'[^a-z0-9]+', '_', ('%s %s' % (name, fname)).lower()).strip('_')
    gen = os.path.join(out_dir, 'gen_%s.json' % tag)
    env = dict(os.environ)
    for k in ('EMC_EU_PRICE', 'EMC_TIME_RATE', 'EMC_FLOORS'):
        env.pop(k, None)
    if rates:
        env['EMC_TIME_RATE'] = json.dumps(rates)
        env['EMC_EU_PRICE'] = json.dumps(prices)
    if fscale is not None:
        floors = json.load(open(os.path.join(HERE, 'hand_values.json')))['floors']['materials']
        env['EMC_FLOORS'] = json.dumps({k: v * fscale for k, v in floors.items()} if fscale else {})
    env['GEN_OUT'] = gen
    if not os.path.exists(gen):
        subprocess.run([sys.executable, 'generate.py'], cwd=HERE, env=env, check=True, stdout=subprocess.DEVNULL)
    audit = subprocess.run([sys.executable, 'audit.py', '--model', gen], cwd=HERE, env=env, check=True,
                           capture_output=True, text=True).stdout
    ppt = subprocess.run([sys.executable, 'prestiges_per_tier.py', '--model', gen], cwd=HERE, env=env, check=True,
                         capture_output=True, text=True).stdout
    open(os.path.join(out_dir, 'audit_%s.txt' % tag), 'w').write(audit)
    open(os.path.join(out_dir, 'ppt_%s.txt' % tag), 'w').write(ppt)
    return (name, fname), gen, audit, ppt


def first_order(rates, prices, recipes, eu):
    """The committed audit.txt's exploits, each paying its EU and time: {group: [(excess EMC/s, excess/run, id)]} for
    those still open (outputs > 1.1 x (inputs + EU + time), gaining 10+ above that, and 5+ EMC/s), and the count."""
    out, n = {}, 0
    for g, i, o, rate, rid in in_game_rows():
        r = recipes.get(rid)
        t = TIERS[r['t']] if r and isinstance(r.get('t'), int) and r['t'] < len(TIERS) else 'ULV'
        secs = max(1, (r or {}).get('d') or 1) / 20
        e = eu.get(rid, (0,))[0] * prices.get(t, 0) if rates else 0
        tc = secs * rates.get(t, 0) if rates else 0
        gain = o - i - e - tc
        n += 1
        if o > 1.1 * (i + e + tc) and gain >= 10 and gain / secs >= 5:
            out.setdefault(group(rid), []).append((gain / secs, gain, rid))
    return out, n


def tool_crafts(gen, recipes, tools):
    """Crafting-table recipes ProjectE doesn't map (they use a GT tool, which comes back): output worth more than the
    consumed inputs at the model's values. [(gain, recipe id)]."""
    val = json.load(open(gen))['val']
    out = []
    for r in recipes:
        if r['type'] != 'minecraft:crafting' or not r['o'] or not r['i']:
            continue
        ings = [[i for i in x['ids'] if i != 'minecraft:air'] for x in r['i']]
        if not any(ids and all(i in tools for i in ids) for ids in ings):
            continue
        cost = 0
        for x, ids in zip(r['i'], ings):
            if not ids or all(i in tools for i in ids):
                continue
            vs = [val.get('i:' + i) for i in ids if val.get('i:' + i)]
            if not vs:
                cost = None
                break
            cost += min(vs) * x['n']
        o = r['o'][0]
        ov = val.get('i:' + o['ids'][0])
        if cost is None or not ov:
            continue
        if ov * o['n'] - cost >= 1:
            out.append((ov * o['n'] - cost, r['id']))
    return sorted(out, reverse=True)


def fmt(x):
    return '{:,.0f}'.format(x)


def main(argv):
    out_dir = argv[0] if argv else os.path.join(HERE, 'time_sweep')
    os.makedirs(out_dir, exist_ok=True)
    items, fluids, tags, recs = load_dump(os.path.join(HERE, 'dump.txt.xz'))
    recipes = {r['id']: r for r in recs if r.get('gt')}
    tools = {i for t, ids in tags.items() if t.startswith('gtceu:crafting_tools/') for i in ids}
    eu = load_eu()
    sched = [(n, r) + eu_schedule(r) for n, r in SCHEDULES]
    jobs = [('baseline (no time, no EU)', None, None, f, s) for f, s in FLOOR_VARIANTS]
    jobs += [(n, r, p, f, s) for n, r, p, _, _ in sched for f, s in FLOOR_VARIANTS]
    with ThreadPoolExecutor(4) as ex:
        res = {k: (gen, a, p) for k, gen, a, p in ex.map(lambda j: run(j, out_dir), jobs)}
    gnames = [g[0] for g in GROUPS]
    ppt_tiers = ['LV', 'MV', 'HV', 'EV', 'IV', 'LUV', 'ZPM', 'UV']

    print('# Time in EMC: sweep (#64)')
    print()
    print('R is EMC per machine-second at the recipe\'s tier; the EU price per tier is the cheapest generator\'s '
          '(fuel + generator time x R) / EU. Pass 2 re-derives the EU price from the model\'s values (with floors).')
    for name, rates, prices, who, gen in sched:
        p2, who2, _ = eu_schedule(rates, res[(name, 'floors')][0])
        print()
        print('## %s' % name)
        print()
        print('| Tier | R (EMC/s) | EMC/EU | Set by | Pass 2 EMC/EU | Pass 2 set by |')
        print('|---|---:|---:|---|---:|---|')
        for t in TIERS[1:]:
            print('| %s | %g | %.3g | %s | %.3g | %s |' % (t, rates[t], prices[t], who[t], p2[t], who2[t]))
        # first order
        fo, n = first_order(rates, prices, recipes, eu)
        allrows = sorted((x for v in fo.values() for x in v), reverse=True)
        print()
        print('In-game exploits still open, first order: %d of %d (gaining 100+ per run: %d). By group: %s.' % (
            len(allrows), n, sum(1 for x in allrows if x[1] >= 100),
            '; '.join('%s %d' % (g, len(fo.get(g, []))) for g in gnames)))
        print('Worst: %s.' % '; '.join('%s +%s EMC/s above time (%s per run)' % (rid, fmt(s), fmt(g))
                                       for s, g, rid in allrows[:5]))
        # model audit and Prestiges
        print()
        print('| Floors | Exploits (100+/run) | Worst EMC/s above time | %s |' % ' | '.join(ppt_tiers))
        print('|---|---:|---|%s' % ('---:|' * len(ppt_tiers)))
        for fname, _ in FLOOR_VARIANTS:
            for key in (('baseline (no time, no EU)', fname), (name, fname)):
                if key[0].startswith('baseline') and name != SCHEDULES[0][0]:
                    continue
                _, audit, ppt = res[key]
                ex = sections(audit)['Exploits (gaining recipes pricing should fix)']
                rows = [ln for ln in audit.split('## Exploits')[1].split('## ')[0].splitlines() if ln.startswith('| ') and
                        not ln.startswith('| Gain')]
                worst = max(rows, key=lambda ln: float(ln.split('|')[5].replace(',', ''))) if rows else None
                w = '%s (%s)' % (worst.split('|')[5].strip(), worst.split('|')[7].strip()) if worst else '-'
                p = prestiges(ppt)
                print('| %s%s | %d (%d) | %s | %s |' % (fname, ' (baseline)' if key[0].startswith('baseline') else '',
                      len(ex), sum(1 for d, _ in ex if d >= 100), w,
                      ' | '.join('%.1f (%.0f M)' % (p[t][1], p[t][0] / 1e6) for t in ppt_tiers)))
        # base earnings
        print()
        print('Base earnings from time: %d machines at the tier, 1 A at V[tier] each, powered by the price-setting '
              'generator; every machine and generator running all hour with its outputs banked:' % BASE_MACHINES)
        print()
        print('| Tier | Machines EMC/h | Generators EMC/h | Total EMC/h | EU cost/h (fuel + time) | Base hours per Run '
              '(net EMC/Run) | Base hours to earn the kit\'s added cost (no floors) |')
        print('|---|---:|---:|---:|---:|---:|---:|')
        pn = prestiges(res[(name, 'no floors')][2])
        p0 = prestiges(res[('baseline (no time, no EU)', 'no floors')][2])
        for t in TIERS[1:]:
            g = gen[t]
            eus = BASE_MACHINES * V[t] * 20
            gtime = sum(k * rates.get(tt, 0) for tt, k in g[4].items()) / g[2] * eus
            m = BASE_MACHINES * rates[t]
            total = (m + gtime) * 3600
            k = t.upper()
            print('| %s | %s | %s | %s | %s | %.1f | %.1f |' % (t, fmt(m * 3600), fmt(gtime * 3600), fmt(total),
                  fmt(eus * prices[t] * 3600), RUN_NET[k] / total, (pn[k][0] - p0[k][0]) / total))
        # pumps
        pmin = min(prices[t] for t in TIERS[1:])
        print()
        print('Step-down pump (a tier\'s recipe at 1 A of V[tier], run on the cheapest EU anywhere, %.3g EMC/EU): EMC/s '
              'per machine on top of its time R, and as a share of R (with one flat EU price, the cheapest anywhere, '
              'it is 0): %s.' % (pmin, '; '.join(
                  '%s %+.2f (%.0f%% of R)' % (t, V[t] * 20 * (prices[t] - pmin), 100 * V[t] * 20 * (prices[t] - pmin) /
                                               rates[t]) for t in TIERS[1:])))
        def worst_oc(speed):
            w = max(((speed ** k * rates[t] / rates[TIERS[i + k]], t, TIERS[i + k]) for i, t in enumerate(TIERS[1:-1], 1)
                     for k in range(1, len(TIERS) - i)), key=lambda x: x[0])
            return '%.2f x R (%s recipe in a %s machine)' % w
        print()
        print('Overclocking: time earned per machine-second by a recipe run in a higher-tier machine, as a multiple of '
              'that machine\'s R, worst case: non-perfect overclock (2x speed per tier) %s; perfect (4x, EBF coils) '
              '%s.' % (worst_oc(2), worst_oc(4)))
        tc = tool_crafts(res[(name, 'floors')][0], recs, tools)
        base_tc = {rid for _, rid in tool_crafts(res[('baseline (no time, no EU)', 'floors')][0], recs, tools)}
        new = [(g, rid) for g, rid in tc if rid not in base_tc]
        print()
        print('Tool crafting (unmapped, instant) worth more than its inputs: %d, %d of them new (vs baseline); '
              'worst new: %s.' % (len(tc), len(new), '; '.join('%s +%s' % (rid, fmt(g)) for g, rid in new[:5]) or '-'))


if __name__ == '__main__':
    main(sys.argv[1:])
