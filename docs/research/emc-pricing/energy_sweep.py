"""Sweep EU prices through the model, audit and Prestiges per tier (VexedPanda/Mc-incremental#64; ../energy-in-emc.md).

Usage: python3 energy_sweep.py [OUT_DIR] > energy_sweep.txt

For each scenario (an EMC_EU_PRICE, with or without the late-tier floors) it runs generate.py with GEN_OUT, then
audit.py and prestiges_per_tier.py against that model, and summarises: exploits (all, and gaining 100+ EMC per run) by
#63 group, the floored rows, and Prestiges per tier. Price 0 is the model's baseline: the model, not the game, so its
counts differ from the committed audit.txt (which reads the in-game values). Takes a few minutes (4 at a time).

The #63 groups are assigned from recipe ids (GROUPS, first match wins): an approximation of #63's lists.
"""
import json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
NO_FLOORS = '{}'
SCENARIOS = [  # (name, EMC_EU_PRICE or None, EMC_FLOORS or None)
    ('0 (baseline)', None, None),
    ('5e-5 (derived, H = 100 h)', '5e-5', None),
    ('4e-4 (derived, H = 10 h)', '4e-4', None),
    ('0.0016 (diesel)', '0.0016', None),
    ('rising x2 per tier', json.dumps({'ULV': 0.0008, 'LV': 0.0016, 'MV': 0.0032, 'HV': 0.0064, 'EV': 0.0128,
                                       'IV': 0.0256, 'LuV': 0.0512, 'ZPM': 0.1024, 'UV': 0.2048}), None),
    ('rising x4 per tier', json.dumps({'ULV': 0.0004, 'LV': 0.0016, 'MV': 0.0064, 'HV': 0.0256, 'EV': 0.1024,
                                       'IV': 0.4096, 'LuV': 1.6384, 'ZPM': 6.5536, 'UV': 26.2144}), None),
    ('0.04 (median break-even)', '0.04', None),
    ('0, no floors', None, NO_FLOORS),
    ('5e-5, no floors', '5e-5', NO_FLOORS),
    ('0.0016, no floors', '0.0016', NO_FLOORS),
    ('rising x2, no floors', None, NO_FLOORS),
    ('rising x4, no floors', None, NO_FLOORS),
]
SCENARIOS[10] = ('rising x2, no floors', SCENARIOS[4][1], NO_FLOORS)
SCENARIOS[11] = ('rising x4, no floors', SCENARIOS[5][1], NO_FLOORS)
GROUPS = [
    ('3 refinery and fuel', r'diesel|gasoline|fuel|naphtha|octane|refinery_gas|desulfurize|distill_|cracked|biomass|oil|'
                            r'lpg|butane|propane|toluene|benzene_from|ethanol'),
    ('2 ore chains', r'platinum|pgs|palladium|rhodium|ruthenium|iridium|osmium|naquad|rare_earth|bauxite|phosphoric_acid|'
                     r'prussian|crystal_chip|rarest|inert_metal|sludge|lead_zinc|tetrahedrite|gallium|uranium|monazite|'
                     r'bastnasite|sheldonite|pentlandite|indium|sphalerite|tungst|scheelite|molybd|titanium|rutile'),
    ('1 cheap inputs split into elements', r'decomposition_(electrolyzing|centrifuging)_+(biotite|andesite|basalt|potash|'
                                           r'clay|potassium_feldspar|granite|diorite|marble|redstone|lithium_chloride|'
                                           r'glyceryl|mercury_barium|.*stone|.*ite)|ash_separation|lava_separation|'
                                           r'glowstone_separation|soul_sand|endstone|netherrack|dust_separation'),
    ('4 chemistry splitting gases', r'chemical_reactor|electrolyzer|isoprene|polybenzimidazole|allyl|ammonia|methane|'
                                    r'ethane|ethylene'),
    ('5 other (lathes)', r'lathe/'),
    ('5 other', r'.'),
]


def in_game_rows():
    """The committed audit.txt's exploits (in-game values): [(gain, inputs, outputs, recipe id)]."""
    rows, sec = [], None
    for line in open(os.path.join(HERE, 'audit.txt')):
        if line.startswith('## '):
            sec = line
        m = re.match(r'\| ([-\d,]+) \| ([\d,]+) \| ([\d,]+) \| [^|]* \| ([\d,.]+) \| \S+ \| (\S+) \|', line)
        if m and sec and 'Exploits' in sec:
            g, i, o, rate = (float(m.group(k).replace(',', '')) for k in (1, 2, 3, 4))
            rows.append((g, i, o, rate, m.group(5)))
    return rows


def first_order(price):
    """In-game exploits (audit.txt) still open when each recipe pays its own EU at price (a JSON EMC_EU_PRICE), with
    the in-game values of its inputs and outputs unchanged: {group: (open, of which gaining 100+)}."""
    from emcmodel import TIER_NAMES, load_eu
    spec = json.loads(price) if price else 0
    eu = load_eu()
    tiers = {r['id']: r.get('t') for r in RECIPES} if RECIPES else {}
    out = {}
    for g, i, o, rate, rid in in_game_rows():
        t = tiers.get(rid) or 0
        if isinstance(spec, dict):
            p = 0
            for k in TIER_NAMES[:t + 1]:
                p = spec.get(k, p)
        else:
            p = spec
        e = eu.get(rid, (0,))[0] * p
        gain = o - i - e
        secs = (g / rate) if rate else 1
        still = o > 1.1 * (i + e) and gain >= 10 and gain / secs >= 5
        k = group(rid)
        a, b = out.get(k, (0, 0))
        out[k] = (a + still, b + (still and gain >= 100))
    return out


RECIPES = []


def group(rid):
    for name, rx in GROUPS:
        if re.search(rx, rid):
            return name
    return '5 other'


def run(scn, out_dir):
    name, price, floors = scn
    tag = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
    gen = os.path.join(out_dir, 'gen_%s.json' % tag)
    env = dict(os.environ)
    env.pop('EMC_EU_PRICE', None)
    env.pop('EMC_FLOORS', None)
    if price:
        env['EMC_EU_PRICE'] = price
    if floors is not None:
        env['EMC_FLOORS'] = floors
    env['GEN_OUT'] = gen
    if not os.path.exists(gen):
        subprocess.run([sys.executable, 'generate.py'], cwd=HERE, env=env, check=True, stdout=subprocess.DEVNULL)
    audit = subprocess.run([sys.executable, 'audit.py', '--model', gen], cwd=HERE, env=env, check=True,
                           capture_output=True, text=True).stdout
    ppt = subprocess.run([sys.executable, 'prestiges_per_tier.py', '--model', gen], cwd=HERE, env=env, check=True,
                         capture_output=True, text=True).stdout
    open(os.path.join(out_dir, 'audit_%s.txt' % tag), 'w').write(audit)
    open(os.path.join(out_dir, 'ppt_%s.txt' % tag), 'w').write(ppt)
    return name, audit, ppt


def sections(audit):
    out, sec = {}, None
    for line in audit.splitlines():
        if line.startswith('## '):
            sec = line[3:].split(':')[0]
            out[sec] = []
        m = re.match(r'\| ([-\d,]+) \| ([\d,]+) \| ([\d,]+) \| [^|]* \| [^|]* \| (\S+) \| (\S+) \|', line)
        if m and sec:
            out[sec].append((float(m.group(1).replace(',', '')), m.group(5)))
    return out


def prestiges(ppt):
    rows = {}
    for line in ppt.splitlines():
        m = re.match(r'\| (\w+) \| ([\d,]+) \|.*\*\*([\d.]+)\*\* \|', line)
        if m:
            rows[m.group(1)] = (float(m.group(2).replace(',', '')), float(m.group(3)))
    return rows


def main(argv):
    out_dir = argv[0] if argv else os.path.join(HERE, 'energy_sweep')
    os.makedirs(out_dir, exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(lambda s: run(s, out_dir), SCENARIOS))
    gnames = [g[0] for g in GROUPS]
    from emcmodel import load_dump
    RECIPES.extend(r for r in load_dump(os.path.join(HERE, 'dump.txt.xz'))[3] if r.get('gt'))
    print('# Energy in EMC: sweep (#64)')
    print()
    print('## The %d in-game exploits (audit.txt), first order' % len(in_game_rows()))
    print()
    print('Each recipe pays its own EU at the price; every value stays as in game. Open / gaining 100+ EMC per run, by '
          '#63 group:')
    print()
    print('| EU price | %s | Total |' % ' | '.join(gnames))
    print('|---|%s---:|' % ('---:|' * len(gnames)))
    for name, price, floors in SCENARIOS:
        if floors is not None:
            continue
        fo = first_order(price)
        print('| %s | %s | %d / %d |' % (name, ' | '.join('%d / %d' % fo.get(g, (0, 0)) for g in gnames),
                                        sum(v[0] for v in fo.values()), sum(v[1] for v in fo.values())))
    print()
    print('## The model re-run')
    print()
    base = {rid for _, rid in sections(results[0][1])['Exploits (gaining recipes pricing should fix)']}
    print('Exploits by #63 group (all gaining rows / those gaining 100+ EMC per run), floored rows, and how many of the '
          'baseline exploits each price closes.')
    print()
    print('| EU price | %s | Total | Closed of baseline | Floored rows |' % ' | '.join(gnames))
    print('|---|%s---:|---:|---:|' % ('---:|' * len(gnames)))
    for name, audit, _ in results:
        s = sections(audit)
        ex = s['Exploits (gaining recipes pricing should fix)']
        cells = []
        for g in gnames:
            rs = [d for d, rid in ex if group(rid) == g]
            cells.append('%d / %d' % (len(rs), sum(1 for d in rs if d >= 100)))
        closed = len(base - {rid for _, rid in ex})
        print('| %s | %s | %d / %d | %d | %d |' % (name, ' | '.join(cells), len(ex), sum(1 for d, _ in ex if d >= 100),
                                                  closed, len(s.get('Recipes making a floored late-tier material (intended, owner decision 3)', []))))
    print()
    print('Prestiges per tier (kit cost in parentheses, millions of EMC):')
    print()
    tiers = list(prestiges(results[0][2]))
    print('| EU price | %s |' % ' | '.join(tiers))
    print('|---|%s' % ('---:|' * len(tiers)))
    for name, _, ppt in results:
        p = prestiges(ppt)
        print('| %s | %s |' % (name, ' | '.join('%.1f (%.2f)' % (p[t][1], p[t][0] / 1e6) for t in tiers)))
    print()
    print('Baseline exploits still open at each price, by group (recipe ids):')
    for name, audit, _ in results:
        if 'no floors' in name:
            continue
        ex = sections(audit)['Exploits (gaining recipes pricing should fix)']
        print()
        print('- **%s**: ' % name + '; '.join('%s: %d' % (g, sum(1 for _, rid in ex if group(rid) == g and rid in base))
                                              for g in gnames))


if __name__ == '__main__':
    main(sys.argv[1:])
