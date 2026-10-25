"""Offline model of ProjectE's EMC mapping plus the Prestige mod's GT recipe mapper (VexedPanda/Mc-incremental#52).

Reads a server log with the dump.js lines (items with their EMC, fluids, item tags, every recipe) and solves the
value of every item and fluid from a set of fixed values the way ProjectE does: a node's value is its fixed value if
it has one, else the cheapest conversion whose ingredients all have values (kept as a fraction; the game floors it).

Two modes:
- 'game' reproduces what the running Pack does (checked against the dumped in-game values): ProjectE doesn't map
  crafting recipes that use a GT tool (hammer, file, wrench, ...) or that make one.
- 'cost' adds the fallback routes generate.py uses for what 'game' leaves unvalued: a GT tool used in crafting comes
  back (it only loses durability), so it isn't counted, and crafting recipes that make tools count; GT's
  decomposition and recycling recipes (electrolysis, centrifuging, macerating or arc-smelting a part) and the
  byproducts and chanced outputs of every GT recipe split their inputs' cost equally per output unit (an item, or
  1000 mB; chanced outputs at their expected amount). These are fallbacks, never cheaper routes: an equal split isn't a
  real cost, and splitting what another recipe composes would loop values down to nothing.
"""
import json, math, re, zipfile
from collections import defaultdict

TOOL_TAG_PREFIX = 'gtceu:crafting_tools/'
TOOL_ITEM_TAGS = ('c:tools', 'minecraft:pickaxes', 'minecraft:axes', 'minecraft:shovels', 'minecraft:hoes',
                  'minecraft:swords')
BASIC_FORM = re.compile(r'(_ingot|_gem|_dust)$|^minecraft:(iron|gold|copper|netherite)_ingot$'
                        r'|^minecraft:(diamond|emerald|lapis_lazuli|quartz|amethyst_shard|coal|charcoal|redstone)$')
VANILLA_TYPES = ('minecraft:crafting', 'minecraft:smelting', 'minecraft:blasting', 'minecraft:smoking',
                 'minecraft:campfire_cooking', 'minecraft:stonecutting', 'minecraft:smithing')


def load_dump(path):
    """(items {id: in-game EMC}, fluids {id: (source id, listed value, bucket item)}, tags {tag: [ids]}, recipes [dict])."""
    items, fluids, tags, recipes = {}, {}, {}, []
    for line in open(path, encoding='utf-8', errors='replace'):
        i = line.find('EMCDUMP ')
        if i >= 0 and 'EMCDUMP-' not in line:
            _, k, v = line[i:].split()
            items[k] = int(v)
            continue
        i = line.find('FLUIDDUMP ')
        if i >= 0:
            p = line[i:].split()
            fluids[p[1]] = (p[2][4:], int(p[3]), p[4][7:] if len(p) > 4 else None)
            continue
        i = line.find('TAGDUMP ')
        if i >= 0 and 'TAGDUMP-' not in line:
            p = line[i:].rstrip('\n').split(' ', 2)
            tags[p[1]] = p[2].split(',') if len(p) > 2 and p[2] else []
            continue
        i = line.find('RDUMP {')
        if i >= 0:
            recipes.append(json.loads(line[i + 6:]))
    return items, fluids, tags, recipes


class Model:
    """Conversions (output node, output count, {ingredient node: amount}, recipe id) over nodes 'i:<item>',
    'f:<source fluid>' (1000 mB) and 'g:<n>' (an ingredient that accepts several items: worth its cheapest)."""

    def __init__(self, dump, listed, mode='game', pe_jar=None):
        self.items, self.fluids, self.tags, recipes = dump
        self.mode = mode
        self.listed = listed  # fluid id -> EMC per 1000 mB, from fluid_emc files
        self.conv = []
        self.groups = {}
        self.tools = {i for t, ids in self.tags.items() if t.startswith(TOOL_TAG_PREFIX) for i in ids}
        self.tool_items = set(self.tools) | {i for t in TOOL_ITEM_TAGS for i in self.tags.get(t, ())
                                             if i.startswith('gtceu:')}
        self.skipped = defaultdict(int)
        self.fixed = {}
        if pe_jar:
            self._load_pe_defaults(pe_jar)
        for r in recipes:
            why = self._add_gt(r) if r.get('gt') else self._add_vanilla(r)
            if why:
                self.skipped[why] += 1

    # ---- nodes ----
    def group(self, ids, kind='i'):
        ids = frozenset(ids)
        if len(ids) == 1:
            return kind + ':' + next(iter(ids))
        g = self.groups.get((kind, ids))
        if g is None:
            g = 'g:%d' % len(self.groups)
            self.groups[(kind, ids)] = g
            for m in ids:
                self.conv.append((g, 1, {kind + ':' + m: 1}, 'group'))
        return g

    def fluid_node(self, f):
        """1000 mB of a fluid's source; None when it is free (listed at 0, or unlisted water)."""
        src = self.fluids.get(f, (f,))[0]
        if src in self.listed:
            return None if self.listed[src] == 0 else 'f:' + src
        return None if src == 'minecraft:water' else 'f:' + src

    # ---- ProjectE's default values (its jar's pe_custom_conversions) ----
    def members(self, spec):
        if 'tag' in spec:
            return self.tags.get(spec['tag'], [])
        return [spec['id']] if 'id' in spec else []

    def _load_pe_defaults(self, jar):
        with zipfile.ZipFile(jar) as z:
            names = sorted(n for n in z.namelist() if n.startswith('data/projecte/pe_custom_conversions/'))
            files = [json.loads(z.read(n)) for n in names if n.endswith('.json')]
        for d in files:
            for e in d.get('values', {}).get('before', []):
                for m in self.members(e):
                    self.fixed['i:' + m] = e['emc_value']
            # values.conversion entries are setValueFromConversion: the output is fixed at the conversion's cost
            for c in d.get('values', {}).get('conversion', []):
                tot = 0
                for x in c['ingredients']:
                    vs = [self.fixed.get('i:' + m) for m in self.members(x)]
                    vs = [v for v in vs if v]
                    tot += min(vs) * x.get('amount', 1) if vs else float('nan')
                if tot == tot:
                    for m in self.members(c['output']):
                        self.fixed['i:' + m] = tot // c.get('count', 1)
            for g in d.get('groups', {}).values():
                for c in g.get('conversions', []):
                    ing = {}
                    for x in c['ingredients']:
                        mem = self.members(x)
                        if not mem:
                            break
                        node = self.group(mem)
                        ing[node] = ing.get(node, 0) + x.get('amount', 1)
                    else:
                        for m in self.members(c['output']):
                            self.conv.append(('i:' + m, c.get('count', 1), ing, 'projecte default'))

    # ---- ProjectE's vanilla recipe mapper ----
    def _add_vanilla(self, r):
        if r['type'] == 'minecraft:smithing' and not r['i'] and r['o']:
            # The dump can't read a smithing recipe's ingredients. GT's netherite tools are its diamond tools
            # upgraded with a netherite ingot and an upgrade template (ProjectE doesn't map GT tools either way).
            out = r['o'][0]['ids'][0]
            if self.mode == 'cost' and r['id'].endswith('_smithing_transform_from_diamond') and 'netherite' in out:
                base = out.replace('netherite', 'diamond', 1)
                if base in self.items:
                    self.conv.append(('i:' + out, 1, {'i:' + base: 1, 'i:minecraft:netherite_ingot': 1,
                                                       'i:minecraft:netherite_upgrade_smithing_template': 1}, r['id']))
                    return None
            return 'smithing'
        if r['type'] not in VANILLA_TYPES or not r['o'] or not r['i']:
            return 'not mapped'
        out = r['o'][0]
        if out['ids'][0] in self.tool_items and self.mode == 'game':
            return 'makes a tool'
        if out.get('c') and self.mode == 'game':
            return 'makes a stack with data components'  # ProjectE values that stack, not the plain item
        ing = defaultdict(float)
        for x in r['i']:
            ids = [i for i in x['ids'] if i != 'minecraft:air']
            if not ids:
                continue
            if all(i in self.tools for i in ids):
                if self.mode == 'game':
                    return 'uses a tool'
                continue  # a GT tool comes back damaged: not consumed
            ing[self.group(ids)] += x['n']
            if all(i.endswith('_bucket') and i != 'minecraft:bucket' for i in ids):
                ing['i:minecraft:bucket'] -= x['n']  # a filled bucket gives the bucket back
        self.conv.append(('i:' + out['ids'][0], out['n'], dict(ing), r['id']))
        return None

    # ---- the Prestige mod's GT recipe mapper (GtRecipeEmcMapper) ----
    @staticmethod
    def _is_form_change(r):
        ins = [x for x in r['i'] if x['ch'] > 0]
        outs = [x for x in r['o'] + r['fo'] if x['ch'] >= x['mx']]
        return len(ins) == 1 and len(outs) == 1 and bool(ins[0]['ids']) and all(BASIC_FORM.search(i) for i in ins[0]['ids'])

    def gt_sides(self, r):
        """(inputs, outputs) as {node: amount in thousandths}, or a reason string when the mapper skips the recipe."""
        inp, out = defaultdict(int), defaultdict(int)
        for x in r['i']:
            if x['ch'] == 0 or x.get('cu') == 'IntCircuitIngredient':
                continue
            cu = (x.get('cu') or '').split('.')[-1]
            if cu.startswith('IntProvider') or cu.startswith('FluidContainer'):
                return 'custom ingredient'
            if not x['ids']:
                return 'empty ingredient'
            inp[self.group(x['ids'])] += x['n'] * 1000
        for x in r['fi']:
            if x['ch'] == 0:
                continue
            if x['cl'].split('.')[-1].startswith('IntProvider') or not x['ids']:
                return 'unsupported fluid'
            nodes = [self.fluid_node(f) for f in x['ids']]
            if any(n is None for n in nodes):
                continue
            inp[nodes[0] if len(set(nodes)) == 1 else self.group([n[2:] for n in nodes], 'f')] += x['n']
        for x in r['o']:
            if x['ch'] < x['mx']:
                continue
            if len(x['ids']) != 1:
                return 'ambiguous output'
            if x.get('c') and self.mode == 'game':
                return 'makes a stack with data components'
            out['i:' + x['ids'][0]] += x['n'] * 1000
        for x in r['fo']:
            if x['ch'] < x['mx']:
                continue
            if x['cl'].split('.')[-1].startswith('IntProvider') or len(x['ids']) != 1:
                return 'unsupported fluid'
            n = self.fluid_node(x['ids'][0])
            if n is not None:
                out[n] += x['n']
        consumed = bool(inp)  # anything but free fluids (and catalysts) goes in
        for node in list(out):
            if node in inp:
                net = out.pop(node) - inp.pop(node)
                if net > 0:
                    out[node] = net
                elif net < 0:
                    inp[node] = -net
        if not out and (self.mode != 'cost' or not any(x['ch'] < x['mx'] for x in r['o'])):
            return 'no output'
        if consumed and not inp:
            return 'consumes only what it makes'
        return inp, out

    def _add_gt(self, r):
        cat = r.get('cat') or ''
        recycling = cat.endswith('_recycling') and not self._is_form_change(r)
        if recycling and self.mode == 'game':
            return 'recycling'
        # In cost mode both are fallbacks: every output gets an equal share (below).
        decomposition = recycling or 'decomposition_' in r['id'].split(':', 1)[1]
        if decomposition and self.mode == 'game':
            return 'decomposition'
        sides = self.gt_sides(r)
        if isinstance(sides, str):
            return sides
        inp, out = sides
        prim = next(iter(out), None)
        if self.mode == 'cost':
            # Fallback costs for what the mapper doesn't value: the other guaranteed outputs (byproducts), chanced
            # outputs (at their expected amount), and every output of a decomposition. Each output unit (an item, or
            # 1000 mB of fluid) costs an equal share of the inputs.
            shares = dict(out)
            for x in r['o']:
                if x['ch'] < x['mx'] and len(x['ids']) == 1:
                    node = 'i:' + x['ids'][0]
                    shares[node] = shares.get(node, 0) + x['n'] * 1000 * x['ch'] / x['mx']
            units = sum(shares.values())
            for node, n in shares.items():
                if (node != prim or decomposition) and n > 0:
                    self.conv.append((node, n / 1000, {k: v * n / units / 1000 for k, v in inp.items()},
                                      r['id'] + ' (share)'))
            if decomposition or prim is None:
                return None
        amounts = dict(inp)
        for node, n in out.items():
            if node != prim and node.startswith('f:') and node[2:] in self.listed:
                amounts[node] = amounts.get(node, 0) - n
        amounts = {k: v for k, v in amounts.items() if v}
        g = out[prim]
        for v in amounts.values():
            g = math.gcd(g, abs(v))
        self.conv.append((prim, out[prim] // g, {k: v / g for k, v in amounts.items()}, r['id']))
        return None

    # ---- solving ----
    def solve(self, fixed, max_rounds=500):
        """node -> value: fixed values win; every other node takes its cheapest conversion. Values stay fractions, as
        in ProjectE, which floors them only at the end (so an item costing less than 1 EMC ends up at 0). A
        conversion with no ingredients, or one costing 0 or less, gives nothing."""
        val = {k: v for k, v in fixed.items() if v > 0}
        by_ing = defaultdict(list)
        for c in self.conv:
            for k in c[2]:
                by_ing[k].append(c)
        dirty = list(self.conv)
        for _ in range(max_rounds):
            if not dirty:
                break
            nxt = {}
            for c in dirty:
                out, cnt, ing, _src = c
                if out in fixed:
                    continue
                if not ing:
                    continue
                tot = 0.0
                for k, a in ing.items():
                    v = val.get(k)
                    if v is None:
                        break
                    tot += a * v
                else:
                    if tot <= 0:
                        continue
                    v = tot / cnt
                    if v < val.get(out, math.inf) * (1 - 1e-12):
                        val[out] = v
                        for c2 in by_ing[out]:
                            nxt[id(c2)] = c2
            dirty = list(nxt.values())
        return val

    def best(self, val, node):
        """The conversion that gives node its value, for explaining a result."""
        for c in self.conv:
            if c[0] != node:
                continue
            try:
                tot = sum(a * val[k] for k, a in c[2].items())
            except KeyError:
                continue
            if c[2] and tot > 0 and abs(tot / c[1] - val.get(node, -1)) <= 1e-9 * max(1, tot / c[1]):
                return c
        return None


def custom_emc_values(path, tags):
    """{node: value} from a custom_emc.json file (item ids and tags)."""
    fixed = {}
    for e in json.load(open(path))['entries']:
        for m in (tags.get(e['tag'], []) if 'tag' in e else [e['id']]):
            fixed['i:' + m] = e['emc']
    return fixed
