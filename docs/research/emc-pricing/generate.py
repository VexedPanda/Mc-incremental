"""Generate the Pack's EMC values (VexedPanda/Mc-incremental#55, re-based in #59, #68, #72 and #81):
pack/config/ProjectE/custom_emc.json and pack/kubejs/data/mcincremental_prestige/fluid_emc/fluids.json.

Usage:
  python3 generate.py [DUMP [PROJECTE_DEFAULTS]] [--write]

DUMP is a server log with the dump.js lines, or the committed dump.txt.xz (the default); PROJECTE_DEFAULTS is
ProjectE's jar or the committed projecte_defaults/ (the default). Without --write it only prints the report.
README.md says how to take a new dump.

The rule (owner decision on #72): pin only what no recipe can make from cheaper things, and let recipes set everything
else; ProjectE takes the cheapest route by itself, so nothing is capped. emcmodel.py replays ProjectE and the GT recipe
mapper's first-output conversions offline; the game, read back from a dump, corrects it where they differ.
 1. Fixed values: ProjectE's defaults and hand_values.json (natural items no recipe makes, the overrides of ProjectE
    defaults a recipe undercuts, the 0-EMC Transmutation Tablet). ProjectE's defaults for GT items (its metal and gem
    tags) are gone: the Pack replaces its metals.json with the vanilla entries (#81), and emcmodel.py reads that too.
    Listed fluids: the hand-set ones (water, lava, steam, milk), the free fluids (from nothing or water alone: gas
    collectors, the air scrubber, water electrolysis), per tier, anchored at lava's 64 (LAVA_ANCHOR), the fluids
    hand_values.json lists at a recipe's cost (nitrogen from air, #81) and the floored materials' molten fluids.
    Every other fluid is left to the Prestige mod's GT recipe mapper, which derives it and publishes the value.
 2. Material units (#59): every raw material's dust or gem value comes from rarity (rarity.json) or ProjectE's
    defaults: vanilla materials keep ProjectE's value; every other material takes its rarity price, raised to what
    smelting or decomposing it gives and to its late-tier floor (hand_values.json). A material a recipe makes for less
    (from non-ore inputs, or composed from other units; alloys from their mixer recipe) isn't pinned (PINNED_UNITS):
    the game derives it, and this model's estimate of it only values the ores that yield it; so is a rarity-priced
    material a dump shows the game making for less (game_route_units(), #81). Each pinned unit is pinned on its dust
    or gem and their small and tiny forms; ingots, nuggets, plates and blocks derive from the dust by recipe (#81).
    A raw ore block is worth 9 raw ores (#81).
 3. Rocks are worth their expected yield (rock dust at the rock's own value plus the chanced byproducts: end stone ->
    tungstate, netherrack -> gold), and every ore-processing form (ore blocks, raw ores, crushed, purified and refined
    ores, impure and pure dusts) is worth what its best route yields, so mining and banking equals processing.
 4. What the game leaves at 0 although a recipe makes it from inputs it values (game_roots(): a recipe it can't map,
    or a share split that gives an output nothing) is pinned at this model's value; game_zero.json keeps those, so
    re-runs are stable. Items whose cheapest recipe costs below 1 EMC (which ProjectE floors to 0) are pinned at 1.
 5. A filled bucket is pinned at the empty bucket plus its fluid (listed, or the value the game derives for it).
"""
import json, math, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from emcmodel import Model, load_dump, load_eu, eu_prices, recipe_energy, recipe_time, time_rates  # noqa: E402
from extract_yields import unit as item_unit  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CUSTOM_EMC = os.path.join(REPO, 'pack', 'config', 'ProjectE', 'custom_emc.json')
FLUIDS = os.path.join(REPO, 'pack', 'kubejs', 'data', 'mcincremental_prestige', 'fluid_emc', 'fluids.json')
VANILLA_UNITS = {'redstone': 'minecraft:redstone', 'diamond': 'minecraft:diamond', 'emerald': 'minecraft:emerald',
                 'coal': 'minecraft:coal', 'lapis': 'minecraft:lapis_lazuli', 'nether_quartz': 'minecraft:quartz',
                 'amethyst': 'minecraft:amethyst_shard', 'flint': 'minecraft:flint',
                 'glowstone': 'minecraft:glowstone_dust'}
BUCKET = 'minecraft:bucket'
# Materials that keep ProjectE's default value (vanilla items; trades and the Philosopher's Stone rely on them): the
# item that carries it.
PE_KEPT = {'iron': 'minecraft:iron_ingot', 'gold': 'minecraft:gold_ingot', 'copper': 'minecraft:copper_ingot',
           'redstone': 'minecraft:redstone', 'diamond': 'minecraft:diamond', 'emerald': 'minecraft:emerald',
           'coal': 'minecraft:coal', 'lapis': 'minecraft:lapis_lazuli', 'nether_quartz': 'minecraft:quartz',
           'amethyst': 'minecraft:amethyst_shard', 'flint': 'minecraft:flint', 'glowstone': 'minecraft:glowstone_dust',
           'clay': 'minecraft:clay_ball', 'nether_star': 'minecraft:nether_star'}
# Rock dusts (never priced by rarity: worth their rock) and the block whose ProjectE value they take.
ROCK_DUSTS = {'stone': 'minecraft:cobblestone', 'deepslate': 'minecraft:cobbled_deepslate',
              'netherrack': 'minecraft:netherrack', 'endstone': 'minecraft:end_stone', 'andesite': 'minecraft:andesite',
              'diorite': 'minecraft:diorite', 'granite': 'minecraft:granite', 'red_granite': 'gtceu:red_granite',
              'marble': 'gtceu:marble', 'basalt': 'minecraft:basalt', 'blackstone': 'minecraft:blackstone',
              'tuff': 'minecraft:tuff', 'calcite': 'minecraft:calcite'}
ROCKS = set(ROCK_DUSTS)
ROCK_BASE = {'minecraft:deepslate': 'minecraft:cobbled_deepslate'}
# Free fluids (#59): what GT makes from nothing or from water alone (gas collectors, the air scrubber, water
# electrolysis) is priced like other resources that are easy to get at the tier that unlocks them, anchored at lava:
# EMC per 1000 mB = LAVA_ANCHOR * 2^(tier - 1) for the cheapest recipe's voltage tier (LV 64, MV 128, HV 256, ...).
# Fluids made from these (nitrogen, ammonia, nitric acid, ...) derive from them. Water stays free; distilled water,
# ice and steam are water in another form and stay nominal.
LAVA_ANCHOR = 64
# What a material unit may be pinned at (owner decision on #72: pin only what no recipe can make from cheaper things):
# its rarity price (or the cap), raised to what smelting or decomposing it gives, its late-tier floor, or ProjectE's
# default. A unit a recipe makes for less ('recipe cost', 'composition cost', 'alloy': lead from galena, sodium from
# salt, an alloy from its mixer recipe) isn't pinned: the game takes the cheapest route itself. Its unit is still
# this model's estimate of that route, for the ores and rocks that yield it.
PINNED_UNITS = ('rarity', 'rarity cap', 'smelting floor', 'decomposition floor', 'late-tier floor', 'ProjectE default')
VANILLA_NUGGETS_UNITS = {'minecraft:gold_nugget': ('gold', 1 / 9), 'minecraft:iron_nugget': ('iron', 1 / 9)}
WATER_FORMS = {'gtceu:distilled_water': 1, 'gtceu:ice': 1}
NOMINAL = 1  # EMC per 1000 mB of a fluid made from water and air alone


FORM_SCALE = [(re.compile(r'^gtceu:hot_(.+)_ingot$'), 1), (re.compile(r'^gtceu:(.+)_ingot$'), 1),
              (re.compile(r'^gtceu:(.+)_nugget$'), 1 / 9), (re.compile(r'^gtceu:(.+)_block$'), 9),
              (re.compile(r'^gtceu:(.+)_plate$'), 1)]


def mat_unit(item):
    """(material, units) for a material's dust or gem forms, ingot, hot ingot, nugget, block or plate; else None."""
    u = item_unit(item)
    if u:
        return u
    for rx, k in FORM_SCALE:
        m = rx.match(item)
        if m and not m.group(1).startswith(('raw_', 'double_', 'dense_')):
            return m.group(1), k
    return None


def unit_items(m):
    return ['gtceu:%s_dust' % m, 'gtceu:%s_gem' % m] + ([VANILLA_UNITS[m]] if m in VANILLA_UNITS else [])


class Generator:
    def __init__(self, log, jar):
        self.dump = load_dump(log)
        self.items, self.fluids, self.tags, self.recipes = self.dump
        self.jar = jar
        self.hand = json.load(open(os.path.join(HERE, 'hand_values.json')))
        self.hand['items'] = {k: v for g in self.hand['groups'] for k, v in g['items'].items()}
        self.rarity = {m: v['emc'] for m, v in json.load(open(os.path.join(HERE, 'rarity.json')))['materials'].items()}
        y = json.load(open(os.path.join(HERE, 'ore_yields.json')))
        self.ores, self.crushed, self.rocks = y['ores'], y['crushed'], y.get('rocks', {})
        self.floors = self.hand.get('floors', {}).get('materials', {})
        if os.environ.get('EMC_FLOORS'):  # for sweeps (prestiges_per_tier.py tuning): a JSON {material: floor}
            self.floors = json.loads(os.environ['EMC_FLOORS'])
        self.rock_dust_values = {}
        zf = os.path.join(HERE, 'game_zero.json')
        gz = json.load(open(zf)) if os.path.exists(zf) else {}
        self.game_zero = set(gz.get('items', []))  # game_roots() adds this dump's
        self.game_zero_fluids = set(gz.get('fluids', []))
        self.route_units = dict(gz.get('materials', {}))  # game_route_units() adds this dump's
        self.listed = dict(self.hand['fluids'])
        # items and fluids ('i:'/'f:' nodes) the model can't derive but the game can (the Prestige mod's GT mapper
        # splits a recipe's cost by shares and maps crafting with GT tools; the model gives a recipe's cost to its
        # first output and skips tool crafts): valued here at a recipe's ingredient cost, never written, so the game
        # derives them (#72). game_roots() pins the ones a dump shows the game can't.
        self.model_values = {}
        self.pins = {}  # item -> (value, reason)
        self.fluid_reasons = {}
        self.log = []

    # ---- helpers ----
    def models(self):
        self.game = Model(self.dump, self.listed, 'game', self.jar)
        self.cost = Model(self.dump, self.listed, 'cost', self.jar)
        # ProjectE's defaults for GT items (its metal and gem tags) are gone: the Pack's own metals.json replaces
        # ProjectE's (#81), and emcmodel.py reads it, so GT materials are priced by rarity and recipes only.
        leftover = sorted(k for k in self.game.fixed if k.startswith('i:gtceu:') and re.search(r'_(ingot|gem)$', k))
        if leftover:
            self.log.append('WARNING: ProjectE defaults still fix GT items: %s' % ' '.join(leftover))
        self.cost_groups = defaultdict(list)
        for out, _, ing, src in self.cost.conv:
            if src == 'group':
                self.cost_groups[out].append(next(iter(ing)))

    def fixed(self):
        f = dict(self.game.fixed)
        f.update({'i:' + k: v for k, v in self.hand['items'].items()})
        f.update({'i:' + k: v for k, (v, _) in self.pins.items()})
        f.update(self.model_values)
        f.update({'f:' + k: v for k, v in self.listed.items() if v > 0})
        return f

    def solve(self):
        return self.game.solve(self.fixed())

    def unit_value(self, val, m):
        vs = [val.get('i:' + i, 0) for i in unit_items(m)]
        return max(vs) if vs else 0

    def pin(self, item, value, reason):
        if item in self.hand['items']:
            return False
        self.pins[item] = (int(value), reason)
        return True

    # ---- steps ----
    def smelt_floor(self, val, item):
        best = 0
        for r in self.recipes:
            if r['type'] in ('minecraft:smelting', 'minecraft:blasting') and r['o'] and any(item in x['ids'] for x in r['i']):
                o = r['o'][0]
                best = max(best, val.get('i:' + o['ids'][0], 0) * o['n'])
        return best

    def material_units(self, val):
        """Every raw material's unit value (its dust or gem), from rarity or ProjectE's defaults only (#59), so ore
        values never feed back into each other: vanilla materials keep ProjectE's value (iron 256, gold 2,048,
        diamond 8,192, ...); every other material (GT-mined metals included) takes its rarity price, lowered to what
        recipes make it for from non-ore inputs (carbon from coal), raised to what smelting it gives (goethite dust
        smelts to an iron ingot) and to its late-tier floor. A material no Run turns up gets the rarity cap. Rock
        dusts are worth their rock. `val` is the first pass's solve: ProjectE's and the hand values, no pins."""
        cap = max(self.rarity.values())
        mats = set(self.rarity)
        for (unit, _), routes in self.crushed.values():
            mats.add(unit)
            for byp in routes.values():
                mats.update(byp)
        for _, _, byp in self.ores.values():
            mats.update(byp)
        for _, byp in self.rocks.values():
            mats.update(byp)
        mats.update(m for m in PE_KEPT if val.get('i:' + PE_KEPT[m]))  # the nether star's dust follows the star
        units, why = {}, defaultdict(int)
        for m in sorted(mats):
            if m in ROCKS:
                continue
            if m in PE_KEPT:
                v = val.get('i:' + PE_KEPT[m])
                if v:
                    units[m] = (v, 'ProjectE default')
                    continue
            item = next((i for i in unit_items(m) if i in self.items), None)
            v, w = self.rarity.get(m, cap), 'rarity' if m in self.rarity else 'rarity cap'
            derived = [val['i:' + i] for i in unit_items(m) if val.get('i:' + i, 0) >= 1]
            if derived and min(derived) < v:
                v, w = min(derived), 'recipe cost'
            floor = self.smelt_floor(val, item) if item else 0
            if floor > v:
                v, w = floor, 'smelting floor'
            if self.floors.get(m, 0) > v:
                v, w = self.floors[m], 'late-tier floor'
            units[m] = (max(1, math.floor(v)), w)
        self.units = units
        self.recipe_consistency()
        self.alloy_units(val)
        self.game_route_units()
        for v, w in self.units.values():
            why[w] += 1
        self.log.append('material units: %s' % dict(why))

    def game_route_units(self):
        """A material still priced by rarity that the dumped game makes for less (#81) isn't pinned either: its unit
        becomes what the game makes it for (U-238, which the fusion reactor and depleted uranium hexafluoride make
        below its rarity price). The model can't see those routes, as they run through pinned ores; the game, read back
        from a dump, can. Only a dump in which the material's dust is still pinned shows one: its ingot, block (per
        unit) or molten fluid (per 144 mB) below the dust, at 1 EMC or more (each is the dust plus a conversion when made
        from the dust). Once unpinned, the game's own dust can fall further through a byproduct share or a tiny dust it
        floors to 0, so a material found once is kept (game_zero.json 'materials'), and only the materials found so are
        unpinned: a re-run from a dump in which they are unpinned gives the same pins."""
        moved = []
        for m, (v, w) in sorted(self.units.items()):
            if w not in ('rarity', 'rarity cap') or self.floors.get(m):
                continue
            dust = max([self.items.get(i) or 0 for i in unit_items(m)])
            vs = [self.items.get('gtceu:%s_ingot' % m) or 0,
                  (self.items.get('gtceu:%s_block' % m) or 0) / self.block_size(m)]
            f = self.fluids.get('gtceu:' + m)
            if f and f[0] == 'gtceu:' + m:
                vs.append((f[1] or 0) * 144 / 1000)
            vs = [x for x in vs if x >= 1]
            if m not in self.route_units and dust >= v * 0.99 and vs and min(vs) < v * 0.99:
                self.route_units[m] = max(1, math.floor(min(vs)))
            if m in self.route_units:
                self.units[m] = (self.route_units[m], 'recipe cost')
                moved.append('%s %d' % (m, self.units[m][0]))
        self.log.append('rarity-priced materials the game makes for less, left to recipes: %s' % ', '.join(moved))

    def block_size(self, m):
        """Units in material m's block: what its compressor recipe packs into it (9, or 4 for a quartz-like gem)."""
        if not hasattr(self, '_block_sizes'):
            self._block_sizes = {}
            for r in self.recipes:
                if r['type'] == 'gtceu:compressor' and len(r['i']) == 1 and len(r['o']) == 1 and len(r['o'][0]['ids']) == 1:
                    u = mat_unit(r['i'][0]['ids'][0]) if len(r['i'][0]['ids']) == 1 else None
                    b = re.match(r'^gtceu:(.+)_block$', r['o'][0]['ids'][0])
                    if u and b and u[0] == b.group(1) and u[1] == 1:
                        self._block_sizes[u[0]] = r['i'][0]['n'] / r['o'][0]['n']
        return self._block_sizes.get(m, 9)

    def alloy_units(self, val, rounds=8):
        """Alloys (and other mixed materials) are worth what the mixer makes them from (#59, "metals and dusts are
        consistent with their recipes"): the cheapest mixer recipe making a material's dust from material units and
        fixed values, per dust. Without this, v0.3.0's mapper drags an alloy below its components (a gaining
        decomposition lowers what it splits off), and its parts melt into a fluid listed above them."""
        fixed = self.fixed()

        def value(i):
            u = mat_unit(i)
            if u and u[0] in self.units:
                return self.units[u[0]][0] * u[1]
            return fixed.get('i:' + i)

        n = 0
        for _ in range(rounds):
            changed = False
            for r in self.recipes:
                if r['type'] != 'gtceu:mixer' or len(r['o']) != 1 or len(r['o'][0]['ids']) != 1 or r['fo']:
                    continue
                out = r['o'][0]['ids'][0]
                u = item_unit(out)
                if not u or u[1] != 1 or u[0] in ROCKS or (u[0] in self.units and self.units[u[0]][1] != 'alloy'):
                    continue
                cost = 0.0
                for x in r['i']:
                    if x['ch'] == 0:
                        continue
                    vs = [v for v in (value(i) for i in x['ids']) if v]
                    if not vs:
                        break
                    cost += min(vs) * x['n'] * x['ch'] / x['mx']
                else:
                    for x in r['fi']:
                        if x['ch'] > 0 and x['ids']:
                            f = self.fluids.get(x['ids'][0], (x['ids'][0],))[0]
                            cost += self.listed.get(f, self.base_val.get('f:' + f, 0)) * x['n'] / 1000
                    v = max(1, math.floor(cost / r['o'][0]['n']))
                    if u[0] not in self.units or v < self.units[u[0]][0]:
                        if u[0] not in self.units:
                            n += 1
                        self.units[u[0]] = (v, 'alloy')
                        changed = True
            if not changed:
                break
        self.log.append('alloys priced at their mixer recipe: %d' % n)

    def recipe_consistency(self, rounds=20):
        """Keep material units consistent with GT's recipes between materials (#59, "metals and dusts are consistent
        with their recipes"): a material's unit is at least what decomposing it gives (galena electrolysed into lead
        and sulfur) and at most what composing it from other materials costs (a mixer), counting only other units,
        listed fluids and items with fixed values. Rarity-priced and recipe-cost units can move; ProjectE's defaults
        can't."""
        fixed = self.fixed()

        def side_value(xs, fluids, out):
            tot = 0.0
            for x in xs:
                x = dict({'ch': 1, 'mx': 1}, **x)
                if x['ch'] == 0:
                    continue
                if len(x['ids']) != 1 and not out:
                    vs = [item_value(i) for i in x['ids']]
                    vs = [v for v in vs if v is not None]
                    if not vs:
                        return None
                    tot += min(vs) * x['n'] * (x['ch'] / x['mx'] if out else 1)
                    continue
                if len(x['ids']) != 1:
                    return None
                v = item_value(x['ids'][0], strict=out)
                if v is None and out:
                    v = 0
                if v is None:
                    return None
                tot += v * x['n'] * (x['ch'] / x['mx'] if out else 1)
            for x in fluids:
                if x['ch'] == 0:
                    continue
                f = self.fluids.get(x['ids'][0], (x['ids'][0],))[0] if x['ids'] else None
                if f == 'minecraft:water':
                    continue
                # an input fluid nothing lists is costed at what recipes make it for; an output one counts 0 (both
                # err towards lower units)
                fv = self.listed.get(f) if out else self.listed.get(f, self.base_val.get('f:%s' % f))
                if fv is None:
                    if out:
                        continue
                    return None
                tot += fv * x['n'] / 1000 * (x['ch'] / x['mx'] if out else 1)
            return tot

        def item_value(i, strict=False):
            """strict (a decomposition's outputs): only units and fixed values, never a floored material (making
            one gains by design) nor a derived or dumped value."""
            u = mat_unit(i)
            if strict and u and u[0] in self.floors:
                return 0
            if u and u[0] in self.units:
                return self.units[u[0]][0] * u[1]
            if u and u[0] in ROCKS:
                return 0
            v = fixed.get('i:' + i)
            if strict:
                return v
            if v is None and self.base_val.get('i:' + i, 0) >= 1:
                v = self.base_val['i:' + i]  # what recipes make it for from non-ore inputs
            return v

        movable = lambda m, kinds: m in self.units and self.units[m][1] in kinds

        def decompose(r, ins, apply):
            """A recipe consuming one material unit (plus fluids): its unit is at least what the outputs are worth."""
            if len(ins) != 1 or len(ins[0]['ids']) != 1 or not r['o'] + r['fo']:
                return False
            u = mat_unit(ins[0]['ids'][0])
            if not u or not movable(u[0], ('rarity', 'rarity cap', 'recipe cost', 'decomposition floor')):
                return False
            if any(mat_unit(i) and mat_unit(i)[0] == u[0] for x in r['o'] for i in x['ids']):
                return False  # a form change (gem -> dust, gem -> lens + dust): not a decomposition
            out_v, in_other = side_value(r['o'], r['fo'], True), side_value([], r['fi'], False)
            if out_v is None or in_other is None:
                return False
            floor = (out_v - in_other) / (ins[0]['n'] * u[1])
            if floor > self.units[u[0]][0] * 1.0001 + 1:
                if apply:
                    self.units[u[0]] = (math.ceil(floor), 'decomposition floor')
                return True
            return False

        def compose(r, ins, apply):
            """A recipe making one material unit only: the unit is at most what its inputs cost."""
            main = [x for x in r['o'] if x['ch'] >= x['mx'] and len(x['ids']) == 1 and mat_unit(x['ids'][0])
                    and movable(mat_unit(x['ids'][0])[0], ('rarity', 'rarity cap', 'recipe cost', 'composition cost',
                                                            'decomposition floor'))]
            if not main or main[0] is not next((x for x in r['o'] if x['ch'] >= x['mx']), None):
                return False  # the recipe's first output must be the material it makes
            main = main[:1]
            u = mat_unit(main[0]['ids'][0])
            if any(mat_unit(i) and mat_unit(i)[0] == u[0] for x in ins for i in x['ids']):
                return False
            cost = side_value(ins, r['fi'], False)
            if not cost or cost <= 0:
                return False
            others = [x for x in r['o'] if x is not main[0]]
            net = cost - (side_value(others, r['fo'], True) or 0)
            # byproducts worth more than the inputs (free gases split off): the main output still costs no more
            # than the inputs
            cost = net if net > 0 else cost
            capv = cost / (main[0]['n'] * u[1])
            if capv < self.units[u[0]][0] * 0.9999 - 1:
                if apply:
                    if self.units[u[0]][1] == 'decomposition floor':
                        conflicts.add('%s (%s)' % (u[0], r['id']))
                    else:
                        self.units[u[0]] = (max(1, math.floor(capv)), 'composition cost')
                return True
            return False

        gt = [r for r in self.recipes if r.get('gt') and not (r.get('cat') or '').endswith('_recycling')]
        smelt = [dict(r, i=[dict(x, ch=1, mx=1) for x in r['i']], o=[dict(x, ch=1, mx=1) for x in r['o']], fi=[], fo=[])
                 for r in self.recipes if r['type'] in ('minecraft:smelting', 'minecraft:blasting') and r['o']]
        conflicts = set()
        # Lower first (compositions), then raise (decompositions), so a byproduct priced above what its own
        # synthesis costs is lowered before it can raise its ingredients.
        for step in (compose, decompose, compose):
            for _ in range(rounds):
                changed = False
                for r in gt + (smelt if step is decompose else []):
                    ins = [x for x in r['i'] if x['ch'] > 0]
                    changed |= step(r, ins, True)
                if not changed:
                    break
        if conflicts:
            self.log.append('materials both decomposed into more and composed for less: %s' % ', '.join(sorted(conflicts)))

    def unit_of(self, m):
        if m in self.units:
            return self.units[m][0]
        return self.rock_dust_values.get(m, 0)

    def best_route(self, routes):
        worth = lambda r: sum(n * self.unit_of(m) for m, n in routes[r].items())
        return routes[max(sorted(routes), key=worth)]

    def unit_pins(self):
        """Pin each raw material's dust and gem (and its small and tiny dusts) at its unit value. Its ingot, nugget,
        plate and block aren't pinned (#81): recipes make them from the dust (smelting, the blast furnace, a bender),
        so they derive from it."""
        n, derived = 0, []
        for m, (v, w) in sorted(self.units.items()):
            if w not in PINNED_UNITS:
                derived.append(m)
                continue
            if m in PE_KEPT and w == 'ProjectE default':
                # vanilla materials: GT's dusts follow the vanilla item
                if m not in ('iron', 'gold', 'copper'):
                    for form, k in (('gtceu:%s_dust' % m, 1), ('gtceu:small_%s_dust' % m, 1 / 4),
                                    ('gtceu:tiny_%s_dust' % m, 1 / 9)):
                        if form in self.items and v * k >= 2 and self.pin(form, math.floor(v * k), 'form of %s' % PE_KEPT[m]):
                            n += 1
                    continue
                if 'gtceu:%s_dust' % m in self.items and self.pin('gtceu:%s_dust' % m, v, 'form of %s (ProjectE default)' % PE_KEPT[m]):
                    n += 1
                continue
            for form in ('gtceu:%s_dust' % m, 'gtceu:%s_gem' % m):
                if form in self.items and self.pin(form, v, '%s: %s' % (w, m)):
                    n += 1
            # the small and tiny dusts follow (one made from a cheap fluid would otherwise pack into a full-price dust)
            for form, k in (('gtceu:tiny_%s_dust' % m, 1 / 9), ('gtceu:small_%s_dust' % m, 1 / 4)):
                if form in self.items and v * k >= 2 and self.pin(form, math.floor(v * k), '%s form of %s' % (w, m)):
                    n += 1
        self.log.append('material dusts and gems pinned at their unit value: %d' % n)
        self.log.append('materials a recipe makes for less, left to recipes: %s' % ' '.join(derived))

    def rock_pins(self, val):
        """Rock dusts are worth their rock (ProjectE's value for the block); a rock whose crushing has valuable
        byproducts (end stone -> tungstate, netherrack -> gold, deepslate -> thorium) is worth its expected yield,
        like an ore, when that is more."""
        self.rock_dust_values = {}
        n = 0
        for m, b in ROCK_DUSTS.items():
            v = self.base_val.get('i:' + b, 0)
            if v:
                self.rock_dust_values[m] = v
                if 'gtceu:%s_dust' % m in self.items and self.pin('gtceu:%s_dust' % m, max(1, math.floor(v)),
                                                                 'rock dust: worth its rock %s' % b):
                    n += 1
        for rock, (dust, byp) in sorted(self.rocks.items()):
            base = self.base_val.get('i:' + rock) or self.base_val.get('i:' + ROCK_BASE.get(rock, rock), 0)
            value = base + sum(k * self.unit_of(m) for m, k in byp.items())
            if value >= base + 1 and self.pin(rock, math.floor(value), 'rock yield: %s dust + byproducts' % rock):
                n += 1
        self.log.append('rock blocks and rock dusts pinned: %d' % n)

    def ore_pins(self, val):
        n = 0
        for block, (mat, count, byp) in sorted(self.ores.items()):
            (unit, amount), routes = self.crushed[mat]
            if not self.unit_of(unit):
                self.log.append('ore without a unit value: %s (%s)' % (block, unit))
                continue
            route = self.best_route(routes)
            value = count * (self.unit_of(unit) * amount + sum(n_ * self.unit_of(m) for m, n_ in route.items()))
            value += sum(n_ * self.unit_of(m) for m, n_ in byp.items())
            if self.pin(block, math.ceil(value), 'ore yield: %g crushed %s' % (count, mat)):
                n += 1
        self.log.append('ore blocks and raw ores pinned: %d' % n)

    PROCESSING = re.compile(r'^gtceu:((crushed|purified|refined)_.+_ore|(impure|pure)_.+_dust|raw_.+_block)$')

    def processing_pins(self, val):
        """Every ore-processing form (ore blocks, raw ores, crushed, purified and refined ores, impure and pure dusts)
        is worth what its best route yields (#59, "ore yields use the best route"): a value iteration over the
        recipes that consume one of them alone (macerator, ore washer, chemical bath, thermal centrifuge, sifter,
        centrifuge, smelting, ...), outputs at their material units (or fixed values, or a processing form's own
        value), consumed fluids at their listed value. So no processing step gains, and mining and banking is as good
        as processing."""
        fixed = self.fixed()

        def out_value(i, V):
            if i in V:
                return V[i]
            u = item_unit(i)
            if u and self.unit_of(u[0]):
                return self.unit_of(u[0]) * u[1]
            if i in VANILLA_NUGGETS_UNITS:
                m, k = VANILLA_NUGGETS_UNITS[i]
                return self.unit_of(m) * k
            return fixed.get('i:' + i, 0)

        def fluid(f):  # listed, else what the recipes derive for it
            return self.listed.get(f, val.get('f:' + f, 0))

        steps = defaultdict(list)
        for r in self.recipes:
            ins = [dict({'ch': 1, 'mx': 1}, **x) for x in r['i']]
            ins = [x for x in ins if x['ch'] > 0]
            if len(ins) != 1 or not r['o'] or (r.get('cat') or '').endswith('_recycling'):
                continue
            if r['type'] not in ('minecraft:smelting', 'minecraft:blasting') and not r.get('gt'):
                continue
            for i in ins[0]['ids']:
                if i in self.ores or self.PROCESSING.match(i):
                    steps[i].append((r, ins[0]['n']))
        V = {}
        for _ in range(60):
            changed = False
            for item, rs in steps.items():
                best = V.get(item, 0)
                for r, n in rs:
                    tot = 0.0
                    for x in r['o']:
                        x = dict({'ch': 1, 'mx': 1}, **x)
                        if len(x['ids']) == 1:
                            tot += out_value(x['ids'][0], V) * x['n'] * x['ch'] / x['mx']
                    for x in r.get('fo', []):
                        if len(x['ids']) == 1:
                            f = self.fluids.get(x['ids'][0], (x['ids'][0],))[0]
                            tot += fluid(f) * x['n'] / 1000 * x['ch'] / x['mx']
                    for x in r.get('fi', []):
                        if x['ch'] > 0 and x['ids']:
                            f = self.fluids.get(x['ids'][0], (x['ids'][0],))[0]
                            tot -= fluid(f) * x['n'] / 1000
                    if tot / n > best * 1.0001:
                        best = tot / n
                if best > V.get(item, 0) * 1.0001:
                    V[item] = best
                    changed = True
            if not changed:
                break
        n = 0
        for item, v in sorted(V.items()):
            cur = self.pins.get(item, (0, ''))[0]
            if v >= 1 and math.ceil(v) > cur and self.pin(item, math.ceil(v), 'best processing route yields this'):
                n += 1
        self.log.append('ore-processing forms pinned at their best route: %d' % n)

    RAW_BLOCK = re.compile(r'^(gtceu|minecraft):raw_(.+)_block$')

    def raw_block_pins(self):
        """A raw ore block is worth the 9 raw ores it is compressed from and the forge hammer breaks it back into
        (#81), so neither gains."""
        n = 0
        for item in sorted(self.items):
            m = self.RAW_BLOCK.match(item)
            raw = m and '%s:raw_%s' % (m.group(1), m.group(2))
            v = raw and (self.pins.get(raw, (None,))[0] or self.hand['items'].get(raw))
            if v and self.pin(item, 9 * v, 'raw ore block: 9 x %s' % raw):
                n += 1
        self.log.append('raw ore blocks pinned at 9 raw ores: %d' % n)

    FLOOR_FORMS = {'dust': 1, 'ingot': 1, 'gem': 1, 'hot_ingot': 1, 'plate': 1, 'nugget': 1 / 9, 'tiny_dust': 1 / 9,
                   'small_dust': 1 / 4, 'block': 9}

    def floor_pins(self, val):
        """Late-tier floors (owner decision 3, #59): each listed material's dust and ingot is worth at least its
        floor, so the tiers that need it take 5-10 Prestiges (prestiges_per_tier.py). Products derive upward."""
        n = []
        for m, f in sorted(self.floors.items()):
            # one unit for every form (dust = ingot, so macerating or smelting one into the other gains nothing): the
            # floor, or what the recipes make the dust or ingot for when that is more
            f = max([f] + [val.get('i:gtceu:%s_%s' % (m, s), 0) for s in ('dust', 'ingot')])
            for suffix, k in self.FLOOR_FORMS.items():
                prefix = suffix.split('_')[0] + '_' if suffix in ('hot_ingot', 'tiny_dust', 'small_dust') else ''
                form = 'gtceu:%s%s_%s' % (prefix, m, suffix.split('_')[-1])
                if form in self.items and self.pin(form, math.ceil(max(f * k, val.get('i:' + form, 0) if suffix == 'hot_ingot' else 0)),
                                                   'late-tier floor: %s' % m):
                    n.append(form)
        self.log.append('late-tier floors pinned: %d' % len(n))

    def game_roots(self):
        """Items and fluids the dumped game left at 0 although a recipe makes them from inputs it valued: the game can't
        map that recipe (an output carrying data components, a smithing upgrade, a dyed GT tool) or its GT mapper's
        share split gives that output nothing (some byproducts of distillation and separation). Only those roots are
        pinned (at this model's value; frontier(), game_zero_pins()): what is 0 only because an input was 0 is left to
        recipes, and is pinned on a later re-run only if it is still 0 once its inputs have values. game_zero.json keeps
        them, so a re-run from a dump in which they are pinned (and so valued) gives the same pins."""
        zero = lambda n: (n.startswith('i:') and self.items.get(n[2:], 1) == 0) or (
            n.startswith('f:') and n[2:] != 'minecraft:water' and self.fluids.get(n[2:], (None, 1))[1] == 0)
        members = defaultdict(list)
        for out, _, ing, src in self.cost.conv:
            if out.startswith('g:'):
                members[out].append(next(iter(ing)))
        node_zero = lambda n: all(zero(m) for m in members[n]) if n.startswith('g:') else zero(n)
        roots = set()
        for out, _, ing, src in self.cost.conv:
            if zero(out) and ing and not any(node_zero(k) for k in ing):
                roots.add(out)
        self.game_zero |= {n[2:] for n in roots if n.startswith('i:') and n != 'i:minecraft:air'}
        self.game_zero_fluids |= {n[2:] for n in roots if n.startswith('f:')}
        self.log.append('items and fluids the game leaves at 0 from valued inputs (roots): %d this dump, %d kept' % (
            len(roots), len(self.game_zero) + len(self.game_zero_fluids)))

    def game_zero_pins(self, val):
        """The game's roots (game_roots(): items and fluids it leaves at 0 although a recipe makes them from valued
        inputs, and tiny dusts it floors to 0) that frontier() hasn't pinned yet, at the model's value (at least 1)."""
        # a tiny or small form is worth its share of what it packs into (9 tiny dusts -> 1 dust)
        packs = {}
        for r in self.recipes:
            ids = {i for x in r['i'] for i in x['ids']}
            if len(ids) == 1 and r['o'] and len(r['o'][0]['ids']) == 1 and r['type'] == 'minecraft:crafting':
                packs[next(iter(ids))] = (r['o'][0]['ids'][0], r['o'][0]['n'] / sum(x['n'] for x in r['i']))
        n = 0
        for item in sorted(self.game_zero):
            if item in self.pins or item in self.hand['items']:
                continue
            v = val.get('i:' + item)
            if item in packs:
                big, k = packs[item]
                # the big form's pin, else what the game makes it for (the dump), else the model's value
                bv = self.pins.get(big, (None,))[0] or self.items.get(big) or val.get('i:' + big)
                if bv:
                    v = bv * k
            if v and self.pin(item, max(1, math.floor(v)), 'the game leaves it at 0: pinned at its model value'):
                n += 1
        for f in sorted(self.game_zero_fluids):
            v = val.get('f:' + f)
            if f not in self.listed and v:
                self.listed[f] = max(1, math.floor(v))
                self.fluid_reasons[f] = 'the game leaves it at 0: its model value'
                n += 1
        self.log.append('items and fluids the game leaves at 0, pinned: %d' % n)

    def frontier(self, max_rounds=3000):
        """Value items and fluids still at 0 in the model at the ingredient cost of a recipe its game mode can't map,
        one step at a time, so that everything made from them is valued too (model_values: not written)."""
        total = 0
        for rnd in range(max_rounds):
            val = self.solve()
            new = {}
            for out, cnt, ing, src in self.cost.conv:
                if out in val or not ing or out.startswith('g:') or out[2:] in self.hand['items']:
                    continue
                tot = 0.0
                for k, a in ing.items():
                    x = val.get(k)
                    if k.startswith('g:'):
                        x = self._group_value(val, k)  # the cost model's groups: worth the cheapest valued member
                    if x is None:
                        break
                    tot += a * x
                else:
                    if tot <= 0:
                        continue
                    cost = tot / cnt
                    if out not in new or cost < new[out][0]:
                        new[out] = (cost, src)
            if not new:
                break
            for out, (cost, src) in new.items():
                v = max(1, math.floor(cost + 1e-9))
                if out.startswith('f:') and out[2:] in self.game_zero_fluids:
                    self.listed[out[2:]] = v
                    self.fluid_reasons[out[2:]] = 'the game leaves it at 0: ingredient cost of %s' % src
                elif out.startswith('i:') and out[2:] in self.game_zero:
                    self.pin(out[2:], v, 'the game leaves it at 0: ingredient cost of %s%s' % (
                        src, ' (below 1 EMC, rounded up)' if cost < 1 else ''))
                else:
                    self.model_values[out] = v
            total += len(new)
        self.log.append('items and fluids the game derives but the model can\'t, valued at a recipe\'s ingredient cost: '
                        '%d in %d rounds' % (total, rnd + 1))

    def _group_value(self, val, g):
        vs = [val[m] for m in self.cost_groups.get(g, ()) if m in val]
        return min(vs) if vs else None

    def source_fluids(self):
        return sorted({v[0] for v in self.fluids.values()} - {'minecraft:empty'})

    def bucket_pins(self, val):
        """A filled bucket is worth the empty bucket plus its fluid: the listed value, else what the game derives for
        it (the dump's FLUIDDUMP value: the Prestige mod publishes the value its GT recipe mapper derives for an
        unlisted fluid), else this model's. ProjectE can't map a filled bucket, so each is pinned."""
        empty = val.get('i:' + BUCKET)
        n, unvalued = 0, []
        for f, (src, dumped, bucket) in sorted(self.fluids.items()):
            if f != src or f == 'minecraft:empty':
                continue
            v = self.listed.get(f)
            if v is None:
                v = dumped or math.floor(val.get('f:' + f, 0) + 1e-9)
            if not v and f not in self.listed:
                unvalued.append(f)
                continue
            if bucket and bucket not in (BUCKET, 'minecraft:air') and self.pin(bucket, empty + v, 'empty bucket + %s' % f):
                n += 1
        self.unvalued_fluids = unvalued
        self.log.append('filled buckets pinned: %d' % n)

    def floor_fluids(self):
        """A floored material's molten fluid and plasma are listed at its floor, 144 mB per ingot, so parts cast from
        them don't undercut the floored ingot (hand_values.json floors)."""
        n = []
        sources = set(self.source_fluids())
        for m, floor in sorted(self.floors.items()):
            for f in ('gtceu:' + m, 'gtceu:%s_plasma' % m):
                if f in sources:
                    self.listed[f] = math.ceil(floor * 1000 / 144)
                    self.fluid_reasons[f] = 'late-tier floor (144 mB per ingot)'
                    n.append(f)
        self.log.append('floored molten fluids and plasmas listed: %d' % len(n))

    def free_fluids(self):
        """Fluids GT makes from nothing or from water alone (gas collectors, the air scrubber, water electrolysis)
        are listed per tier, anchored at lava (LAVA_ANCHOR); see the constant."""
        tiers = {}
        src = lambda i: self.fluids.get(i, (i,))[0]
        for r in self.recipes:
            if not r.get('gt') or any(x['ch'] > 0 and x.get('cu') != 'IntCircuitIngredient'
                                      and not (x.get('cu') or '').endswith('IntCircuitIngredient') for x in r['i']):
                continue
            if not all(any(src(i) == 'minecraft:water' for i in x['ids']) for x in r['fi'] if x['ch'] > 0):
                continue
            for x in r['fo']:
                if x['ch'] >= x['mx'] and len(x['ids']) == 1:
                    f = src(x['ids'][0])
                    if f != 'minecraft:water':
                        tiers[f] = min(tiers.get(f, 99), max(1, r.get('t') or 1))
        self.free_tiers = tiers
        n = []
        for f, t in sorted(tiers.items()):
            if f in self.hand['fluids']:
                continue
            v = WATER_FORMS.get(f, LAVA_ANCHOR * 2 ** (t - 1))
            self.listed[f] = v
            self.fluid_reasons[f] = 'free fluid: tier %d' % t if f not in WATER_FORMS else 'water in another form'
            n.append('%s %d' % (f, v))
        self.log.append('free fluids (from nothing or water alone), per tier: %s' % ', '.join(n))

    def recipe_cost_fluids(self):
        """Fluids hand_values.json lists at a recipe's cost (fluids_at_recipe_cost: nitrogen from air, #81), the
        cheapest of the recipes named: the consumed fluids at their listed value (else what the game derives for them,
        from the dump) plus the machine time and EU, less the other listed fluids and the items it also gives, per
        1000 mB of the fluid. Runs after free_fluids(), which lists the free inputs."""
        src = lambda i: self.fluids.get(i, (i,))[0]
        fluid = lambda i: self.listed.get(src(i), self.fluids.get(src(i), (None, 0))[1] or 0)
        rates, prices, eu = time_rates(), eu_prices(), load_eu()
        by_id = {r['id']: r for r in self.recipes}
        n = []
        for f, rids in sorted(self.hand.get('fluids_at_recipe_cost', {}).get('fluids', {}).items()):
            costs = []
            for rid in rids:
                r = by_id[rid]
                assert not [x for x in r['i'] if x['ch'] > 0], 'item inputs are not costed: %s' % rid
                cost = sum(fluid(x['ids'][0]) * x['n'] / 1000 for x in r['fi'] if x['ch'] > 0)
                cost += sum((c or (0, 0, 0))[2] for c in (recipe_time(r, rates), recipe_energy(r, eu, prices)))
                amount = 0
                for x in r['fo']:
                    k = x['n'] * x['ch'] / x['mx'] / 1000
                    if src(x['ids'][0]) == f:
                        amount += k
                    else:
                        cost -= self.listed.get(src(x['ids'][0]), 0) * k
                cost -= sum((self.items.get(x['ids'][0]) or 0) * x['n'] * x['ch'] / x['mx'] for x in r['o'])
                costs.append((cost / amount, rid))
            cost, rid = min(costs)
            self.listed[f] = max(1, math.floor(cost))
            self.fluid_reasons[f] = 'recipe cost of %s' % rid
            n.append('%s %d (%s)' % (f, self.listed[f], ', '.join('%s %.0f' % (r, c) for c, r in costs)))
        self.log.append('fluids listed at a recipe\'s cost: %s' % '; '.join(n))

    def unobtainable_materials(self, val):
        """A material dust still at 0 after everything above has no recipe that makes it from anything valued (GT
        registers materials this Pack never generates, such as damascus steel). Its dust gets its rarity price, or the
        rarity cap when no Run ever turns it up, so everything made from it is derived; it is never obtained, so the
        value is never used."""
        cap = max(self.rarity.values())
        n = []
        for item in sorted(self.items):
            if not (item.startswith('gtceu:') and item.endswith('_dust')) or val.get('i:' + item):
                continue
            m = item[6:-5]
            if m.startswith(('small_', 'tiny_', 'impure_', 'pure_')):
                continue
            if self.pin(item, self.rarity.get(m, cap), 'unobtainable material %s: rarity price or cap' % m):
                n.append(m)
        self.log.append('dusts of materials nothing makes, at their rarity price or the cap: %s' % ' '.join(n))

    def smelted_ores(self, val):
        """Ores GT has no macerator recipe for (vanilla nether quartz ore, ancient debris) are worth what smelting
        them gives."""
        n = []
        for item in self.tags.get('c:ores', []):
            if val.get('i:' + item):
                continue
            v = self.smelt_floor(val, item)
            if v and self.pin(item, v, 'ore without a macerator recipe: what smelting it gives'):
                n.append(item)
        self.log.append('ores valued at their smelting product: %s' % ' '.join(n))

    def sub_unit(self):
        """ProjectE floors values at the end, so an item whose cheapest recipe costs less than 1 EMC (a slab cut
        from 1-EMC stone, glass from sand and a whiff of oxygen) ends up at 0. Pin those at 1 (and those below 5,
        which the game may cost lower, at their floor)."""
        n = 0
        for _ in range(20):
            val = self.solve()
            # Below 5, not 1: the game sometimes finds a cheaper route than this model does (a pin below 5 can't
            # make 100 EMC even nine at a time). When the dump
            # was taken from a server running these values, an item it shows at 2 or less that this model costs under
            # 20 EMC is rounding too (its base is cheaper in the game, e.g. tiny silicon dust from 8-EMC silicon); it
            # stays pinned on the next run, whose dump shows it at its pin. Only while nine of them gain under 100
            # EMC at that pin, though: with machine time counted (#68) a tiny dust unpacked from a dust costs well
            # above its old pin (tiny potash: 17), and pinning it at 1 would let nine of them pack into a dust at a
            # gain.
            def is_low(k, v):
                g = self.items.get(k[2:])
                return v < 5 or (g is not None and g <= 2 and v < 20 and 9 * (v - g) < 100)
            low = [k for k, v in val.items() if k.startswith('i:') and is_low(k, v)
                   and k[2:] not in self.hand['items'] and k[2:] not in self.pins]
            if not low:
                break
            for k in low:
                g = self.items.get(k[2:])
                v = val[k] if not g else min(val[k], g)
                if self.pin(k[2:], max(1, math.floor(v)), 'cheapest recipe costs %.3g EMC' % v):
                    n += 1
        self.log.append('items whose cheapest recipe costs less than 1 EMC, pinned at 1: %d' % n)

    def cycle_pins(self, val):
        """Items in a recipe cycle whose byproduct fluid is subtracted on every pass (magnesite -> magnesia + CO2 ->
        magnesite): ProjectE floors on each pass, so the game drives their value down to 1 or 2 EMC. hand_values.json
        lists them; they are pinned at what this model derives for them."""
        for item in self.hand.get('pin_at_derived_value', {}).get('items', []):
            v = val.get('i:' + item)
            if v and v >= 1:
                self.pin(item, math.floor(v), 'recipe cycle the game floors to nothing: pinned at its derived value')
        self.log.append('recipe-cycle items pinned at their derived value: %s' % ' '.join(
            self.hand.get('pin_at_derived_value', {}).get('items', [])))

    PRUNABLE = ('unobtainable', 'cheapest recipe')

    def prune(self):
        """Drop the pins of items the game can now derive by itself (at 2 EMC or more): a pin is only for what
        nothing else values, and a stale pin above a cheaper route is an exploit."""
        prunable = {k for k, (_, why) in self.pins.items() if why.startswith(self.PRUNABLE)}
        fixed = {k: v for k, v in self.fixed().items() if not (k.startswith('i:') and k[2:] in prunable)}
        val = self.game.solve(fixed)
        dropped = [k for k in prunable if val.get('i:' + k, 0) >= 2]
        for k in dropped:
            del self.pins[k]
        self.log.append('pins dropped because the game derives the item: %d' % len(dropped))

    def one_pass(self):
        self.pins = {}
        self.models()
        if not hasattr(self, 'units'):
            # Material units are fixed on the first pass, from ProjectE's and the hand values only (no pins, no
            # derived fluids), so an ore's value never feeds back into a unit.
            self.base_val = self.solve()
            self.material_units(self.base_val)
        self.unit_pins()
        self.floor_pins(self.solve())  # before anything is pinned at an ingredient cost, so those follow the floors
        self.rock_pins(self.solve())
        self.ore_pins(self.solve())
        self.frontier()
        self.unobtainable_materials(self.solve())
        self.frontier()
        self.smelted_ores(self.solve())
        self.frontier()
        self.prune()
        self.processing_pins(self.solve())
        self.raw_block_pins()
        self.cycle_pins(self.solve())
        self.game_zero_pins(self.solve())
        self.sub_unit()

    def run(self):
        """One pass: the listed fluids are the hand-set ones, the free fluids and the floored molten fluids; every
        other fluid is left to the Prestige mod's GT recipe mapper, which derives it from its recipes (#72)."""
        self.free_fluids()
        self.recipe_cost_fluids()
        self.floor_fluids()
        self.models()
        self.game_roots()
        self.game_zero = {k for k in self.game_zero if k in self.items and k != 'minecraft:air'}
        self.one_pass()
        self.models()
        self.bucket_pins(self.solve())
        self.log.append('fluids nothing values (allow-listed): %s' % ' '.join(self.unvalued_fluids))
        return self.solve()

CUSTOM_EMC_COMMENT = (
    "Mc-incremental EMC values (#41, #47, #55, #59, #68, #72, #81). GENERATED by docs/research/emc-pricing/generate.py "
    "from hand_values.json, rarity.json and ore_yields.json there: do not edit by hand, edit those and re-run it. "
    "ProjectE applies this file after its datapack defaults, so these values win. It pins only what no recipe can make "
    "from cheaper things (#72): hand values, every raw material's unit on its dust or gem (rarity or ProjectE's "
    "defaults; ingots, plates and blocks derive from it, #81), the late-tier floors, rocks and every ore-processing form "
    "at their expected yield (a raw ore block at 9 raw ores), what the game can't derive (pinned at a recipe's "
    "ingredient cost), filled buckets (empty bucket + fluid), and the ProjectE tag defaults the Pack overrides (nether "
    "star, blaze rod). ProjectE and the Prestige mod's GT recipe mapper derive everything else. The Transmutation "
    "Tablet is 0: the Prestige mod hands it out. See docs/pocs/poc-1.md.")
FLUIDS_COMMENT = (
    "EMC per 1000 mB of the fluids the Pack lists, for the Prestige mod (ProjectE can't hold fluid values) and its GT "
    "recipe mapper. GENERATED by docs/research/emc-pricing/generate.py: edit hand_values.json there and re-run it. Water "
    "is the one free fluid. Lava and milk are ProjectE's bucket values minus the empty bucket, steam is nominal; fluids "
    "GT makes from nothing or water alone are priced per tier, anchored at lava (LV 64, MV 128, HV 256); nitrogen is "
    "its cost from air (#81); a floored material's molten fluid is its floor per 144 mB. Every other fluid is "
    "unlisted: the GT recipe mapper derives it from its recipes (#72). A filled bucket is worth the empty bucket plus "
    "its fluid (custom_emc.json).")


def write(g):
    entries = dict(g.hand['items'])
    entries.update({k: v for k, (v, _) in g.pins.items()})
    lines = ['  {"id": %s, "emc": %d}' % (json.dumps(k), v) for k, v in sorted(entries.items())]
    # Tags ProjectE's own defaults pin that must follow an item's new value (owner decision 5: c:nether_stars).
    tags = dict(g.hand.get('tags', {}).get('tags', {}))
    lines += ['  {"tag": %s, "emc": %d}' % (json.dumps(k), v) for k, v in sorted(tags.items())]
    with open(CUSTOM_EMC, 'w') as f:
        f.write('{\n "comment": %s,\n "entries": [\n%s\n ]\n}\n' % (json.dumps(CUSTOM_EMC_COMMENT), ',\n'.join(lines)))
    fl = ['  %s: %d' % (json.dumps(k), v) for k, v in sorted(g.listed.items())]
    with open(FLUIDS, 'w') as f:
        f.write('{\n "comment": %s,\n "emc_per_1000_mb": {\n%s\n }\n}\n' % (json.dumps(FLUIDS_COMMENT), ',\n'.join(fl)))
    zero = sorted(k for k, (_, why) in g.pins.items() if why.startswith('the game leaves it at 0'))
    with open(os.path.join(HERE, 'game_zero.json'), 'w') as f:
        json.dump({'comment': 'Generated by generate.py: items and fluids a dump showed at 0 EMC although a recipe makes '
                              'them from inputs the game valued (the game can\'t map that recipe, its share split gives '
                              'them nothing, or it floors a tiny dust), pinned at their model value. Kept so re-runs '
                              'are stable.',
                   'items': zero, 'fluids': sorted(f for f in g.game_zero_fluids if f in g.listed),
                   'materials_comment': 'Rarity-priced materials a dump showed the game making for less through '
                                        'another form (#81), left to recipes, at the unit value first found.',
                   'materials': dict(sorted(g.route_units.items()))}, f, indent=1)
        f.write('\n')
    print('wrote %d item values to %s and %d fluid values to %s' % (len(lines), CUSTOM_EMC, len(fl), FLUIDS))


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    if len(args) > 2:
        sys.exit(__doc__)
    g = Generator(args[0] if args else os.path.join(HERE, 'dump.txt.xz'),
                  args[1] if len(args) > 1 else os.path.join(HERE, 'projecte_defaults'))
    val = g.run()
    for l in g.log:
        print(l)
    zero = sorted(k for k in g.items if k != 'minecraft:air' and val.get('i:' + k, 0) < 1)
    print('items the model leaves at 0 (the smoke test allow-lists the unobtainable ones): %d' % len(zero))
    if '--write' in argv:
        write(g)
    if os.environ.get('GEN_OUT'):
        json.dump({'zero': zero, 'pins': g.pins, 'units': g.units, 'listed': g.listed,
                   'val': {k: v for k, v in val.items() if not k.startswith('g:')}}, open(os.environ['GEN_OUT'], 'w'))


if __name__ == '__main__':
    main(sys.argv[1:])
