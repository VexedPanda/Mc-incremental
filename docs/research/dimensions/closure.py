"""Reachability closure over every recipe in the pack (dumped by zz_dims.js).

Usage: python3 -I closure.py <dims_run1.log> <econ dump1> <econ dump2> <dims_run2.log>
Library-style: functions are imported by report.py via exec.
"""
import json, sys, re
from collections import defaultdict

LOG, D1, D2, LOG2 = sys.argv[1:5]

recipes = []  # (id, type, reqs: list[(items frozenset, fluids frozenset)], outs items set, outs fluids set, dims)
itags, ftags, b2i = {}, {}, {}
for line in open(LOG, encoding='utf-8', errors='replace'):
    i = line.find('[DIMS] ')
    if i < 0: continue
    body = line[i + 7:].rstrip('\n')
    kind, _, rest = body.partition(' ')
    if kind == 'R':
        rid, _, js = rest.partition(' ')
        try: recipes.append((rid, json.loads(js)))
        except Exception: pass
    elif kind == 'ITAG':
        k, _, v = rest.partition(' '); itags[k] = set(v.split(',')) if v else set()
    elif kind == 'FTAG':
        k, _, v = rest.partition(' '); ftags[k] = set(v.split(',')) if v else set()
    elif kind == 'B2I':
        k, _, v = rest.partition(' '); b2i[k] = v

def ing_items(node):
    """Items an ingredient node accepts (None = always satisfied, e.g. programmed circuit)."""
    if isinstance(node, list):
        s = set()
        for x in node:
            r = ing_items(x)
            if r is None: return None
            s |= r
        return s
    if not isinstance(node, dict): return set()
    t = node.get('type')
    if t == 'gtceu:circuit': return None
    if t == 'gtceu:fluid_container':
        return {'FLUID:' + f for f in fl_items(node.get('fluid', {}))}
    if t == 'neoforge:intersection':
        sets = [ing_items(c) for c in node['children']]
        sets = [s for s in sets if s is not None]
        out = sets[0]
        for s in sets[1:]: out = out & s
        return out
    if t == 'neoforge:difference':
        return ing_items(node.get('base'))
    if t == 'neoforge:compound':
        return ing_items(node.get('children', []))
    if 'item' in node and isinstance(node['item'], str): return {node['item']}
    if 'tag' in node: return set(itags.get(node['tag'], set()))
    if 'items' in node:
        v = node['items']
        return set([v] if isinstance(v, str) else [x for x in v if isinstance(x, str)])
    if 'ingredient' in node: return ing_items(node['ingredient'])
    if 'children' in node: return ing_items(node['children'])
    if 'id' in node and isinstance(node['id'], str): return {node['id']}
    return set()

def fl_items(node):
    if isinstance(node, dict):
        if 'ingredient' in node: return fl_items(node['ingredient'])
        if 'tag' in node: return set(ftags.get(node['tag'], set()))
        if 'fluid' in node: return {node['fluid']}
        if 'fluids' in node: return set(node['fluids'])
    if isinstance(node, list):
        s = set()
        for x in node: s |= fl_items(x)
        return s
    return set()

def collect_out(node, items, fluids, top=False):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ('components', 'data', 'nbt'): continue
            if k in ('item', 'id') and isinstance(v, str): items.add(v)
            elif k == 'fluid' and isinstance(v, str): fluids.add(v)
            elif k == 'tag' and isinstance(v, str):
                m = sorted(itags.get(v, ())) or sorted(ftags.get(v, ()))
                if m: (items if v in itags else fluids).add(m[0])
            else: collect_out(v, items, fluids)
    elif isinstance(node, list):
        for x in node: collect_out(x, items, fluids)
    elif isinstance(node, str) and top: items.add(node)

EXCLUDE_IDS = {'gtceu:centrifuge/stone_dust_separation'}
parsed = []
for rid, j in recipes:
    if rid in EXCLUDE_IDS: continue
    typ = j.get('type', '')
    dims = None
    for c in j.get('recipeConditions', []) or []:
        if c.get('type') == 'gtceu:dimension': dims = c.get('dimension')
    reqs = []
    outs_i, outs_f = set(), set()
    if typ.startswith('gtceu:') and 'inputs' in j or 'outputs' in j and isinstance(j.get('outputs'), dict):
        for cap, lst in (j.get('inputs') or {}).items():
            for e in lst:
                c = e.get('content')
                if cap == 'gtceu:item':
                    s = ing_items(c)
                    if s is None: continue
                    reqs.append((frozenset(s), frozenset()))
                elif cap == 'gtceu:fluid':
                    reqs.append((frozenset(), frozenset(fl_items(c))))
        for cap, lst in (j.get('outputs') or {}).items():
            for e in lst:
                c = e.get('content')
                if cap == 'gtceu:item': collect_out(c, outs_i, outs_f)
                elif cap == 'gtceu:fluid': outs_f |= fl_items(c)
    else:
        for k in ('ingredients',):
            for x in j.get(k, []) or []:
                s = ing_items(x)
                if s is not None: reqs.append((frozenset(s), frozenset()))
        if isinstance(j.get('key'), dict):
            for x in j['key'].values():
                s = ing_items(x)
                if s is not None: reqs.append((frozenset(s), frozenset()))
        for k in ('ingredient', 'base', 'addition', 'template', 'input'):
            if k in j:
                s = ing_items(j[k])
                if s is not None: reqs.append((frozenset(s), frozenset()))
        for k in ('result', 'results', 'output'):
            if k in j: collect_out(j[k], outs_i, outs_f, top=True)
    # tool-like ingredients (crafting tools) are made from the same graph; keep them as requirements
    if not outs_i and not outs_f: continue
    parsed.append((rid, typ, reqs, outs_i, outs_f, dims))

def closure(seed_items, seed_fluids, dims_ok, extra_items=()):
    R = set(seed_items) | set(extra_items); F = set(seed_fluids)
    via = {}
    changed = True
    while changed:
        changed = False
        for rid, typ, reqs, oi, of, dims in parsed:
            if dims is not None and dims not in dims_ok: continue
            if oi <= R and of <= F: continue
            ok = True
            for its, fls in reqs:
                if its and not (its & R): ok = False; break
                if fls and not (fls & F): ok = False; break
                if not its and not fls: ok = False; break
            if not ok: continue
            for x in oi - R: via[x] = rid
            for x in of - F: via[x] = rid
            R |= oi; F |= of; changed = True
    return R, F, via

RBYID = {p[0]: p for p in parsed}
def trace(item, via, R, F, depth=0, seen=None, maxd=6):
    seen = seen if seen is not None else set()
    if item in seen or depth > maxd: return
    seen.add(item)
    rid = via.get(item)
    print('  ' * depth + f'{item} <- {rid}')
    if not rid: return
    for its, fls in RBYID[rid][2]:
        pick = sorted(its & R)[:1] + sorted(fls & F)[:1]
        for p in pick: trace(p, via, R, F, depth + 1, seen, maxd)

# ---- Machine gating ----
TIERS = ['ulv', 'lv', 'mv', 'hv', 'ev', 'iv', 'luv', 'zpm', 'uv', 'uhv']
V = [8, 32, 128, 512, 2048, 8192, 32768, 131072, 524288, 2097152]
ALLITEMS = set(b2i.values())
COILS = {'cupronickel': 1800, 'kanthal': 2700, 'nichrome': 3600, 'rtm_alloy': 4500, 'hssg': 5400, 'naquadah': 7200,
         'trinium': 9001, 'tritanium': 10800}
FUSION = [('gtceu:luv_fusion_reactor', 160e6), ('gtceu:zpm_fusion_reactor', 320e6), ('gtceu:uv_fusion_reactor', 640e6)]
RAW = {p[0]: j for p in parsed for j in [None]}
RAWJ = dict(recipes)

def eu_tier(j):
    eu = 0
    for e in (j.get('tickInputs') or {}).get('gtceu:eu', []) or []:
        c = e.get('content')
        if isinstance(c, (int, float)): eu = max(eu, c)
    if eu <= 0: return -1, 0
    for i, v in enumerate(V):
        if eu <= v: return i, eu
    return len(V) - 1, eu

ungated_types = Counter() if 'Counter' in globals() else None
def gate(rid, typ, j):
    """List of alternative requirement sets (each a list of item-alternative frozensets); None = ungated."""
    if not typ.startswith('gtceu:') or 'inputs' not in j and 'outputs' not in j: return None
    path = typ.split(':')[1]
    t, eu = eu_tier(j)
    alts = []
    for i, tn in enumerate(TIERS):
        mid = f'gtceu:{tn}_{path}'
        if mid in ALLITEMS and i >= max(t, 1): alts.append([frozenset([mid])])
    if t <= 1 and f'gtceu:lp_steam_{path}' in ALLITEMS: alts.append([frozenset([f'gtceu:lp_steam_{path}'])])
    if t <= 1 and f'gtceu:hp_steam_{path}' in ALLITEMS: alts.append([frozenset([f'gtceu:hp_steam_{path}'])])
    ctrl = f'gtceu:{path}'
    if path == 'fusion_reactor':
        start = (j.get('data') or {}).get('eu_to_start', 0)
        alts.append([frozenset(c for c, cap in FUSION if cap >= start)])
    elif ctrl in ALLITEMS:
        req = [frozenset([ctrl])]
        if t >= 1:
            req.append(frozenset(f'gtceu:{TIERS[i]}_energy_input_hatch' for i in range(max(t - 1, 1), len(TIERS))))
        temp = (j.get('data') or {}).get('ebf_temp')
        if temp:
            # coil temperature + 100 K per energy tier above MV (assume hatch tier = recipe tier)
            bonus = 100 * max(0, t - 2)
            req.append(frozenset(f'gtceu:{c}_coil_block' for c, k in COILS.items() if k + bonus >= temp))
        alts.append(req)
    if not alts:
        if ungated_types is not None: ungated_types[path] += 1
        return None
    for c in j.get('recipeConditions', []) or []:
        if c.get('type') == 'gtceu:cleanroom':
            need = 'gtceu:sterilizing_filter_casing' if c.get('cleanroom') == 'sterile_cleanroom' else 'gtceu:cleanroom'
            for a in alts: a.append(frozenset([need]))
        if 'research' in c:
            for r in c['research']:
                di = (r.get('data_item') or {}).get('id')
                m = frozenset([f'gtceu:{tn}_scanner' for tn in TIERS]) if di == 'gtceu:data_stick' else frozenset(['gtceu:research_station'])
                for a in alts: a.extend([frozenset([di]), m])
    return alts

GATES = {}
for rid, typ, reqs, oi, of, dims in parsed:
    GATES[rid] = gate(rid, typ, RAWJ.get(rid, {}))

def closure_m(seed_items, seed_fluids, dims_ok, extra_items=()):
    R = set(seed_items) | set(extra_items) | {'FLUID:' + f for f in seed_fluids}; F = set(seed_fluids)
    via = {}
    changed = True
    while changed:
        changed = False
        for rid, typ, reqs, oi, of, dims in parsed:
            if dims is not None and dims not in dims_ok: continue
            if oi <= R and of <= F: continue
            g = GATES[rid]
            if g is not None and not any(all(s & R for s in alt) for alt in g): continue
            ok = True
            for its, fls in reqs:
                if its and not (its & R): ok = False; break
                if fls and not (fls & F): ok = False; break
                if not its and not fls: ok = False; break
            if not ok: continue
            for x in oi - R: via[x] = rid
            for x in of - F: via[x] = rid
            R |= oi; R |= {'FLUID:' + f for f in of}; F |= of; changed = True
    return R, F, via

def whynot(item, R, F, maxr=4):
    n = 0
    for rid, typ, reqs, oi, of, dims in parsed:
        if item not in oi and item not in of: continue
        miss = [sorted(its)[:3] + sorted(fls)[:2] for its, fls in reqs if not ((its & R) or (fls & F))]
        g = GATES.get(rid)
        gm = None
        if g is not None and not any(all(s & R for s in alt) for alt in g):
            gm = [[sorted(s)[:2] for s in alt if not (s & R)] for alt in g][:3]
        print(f'  {rid}: missing {miss} gate {gm}')
        n += 1
        if n >= maxr: break
