"""Generate the Pack's EMC values (VexedPanda/Mc-incremental#55): pack/config/ProjectE/custom_emc.json and
pack/kubejs/data/mcincremental_prestige/fluid_emc/fluids.json.

Usage:
  python3 generate.py [DUMP [PROJECTE_DEFAULTS]] [--write]

DUMP is a server log with the dump.js lines, or the committed dump.txt.xz (the default); PROJECTE_DEFAULTS is
ProjectE's jar or the committed projecte_defaults/ (the default). Without --write it only prints the report.
README.md says how to take a new dump.

What it does (emcmodel.py replays ProjectE and the Prestige mod's GT recipe mapper offline):
 1. Fixed values: ProjectE's defaults and hand_values.json. Fluids GT makes from water and air alone are a nominal 1.
 2. Every ore block and raw ore is worth what fully processing it yields (ore_yields.json): its crushed ores' unit
    plus the expected byproducts. A material's unit is the value its dust or gem already has, at least what smelting
    it gives (goethite dust smelts to an iron ingot); a material with neither is priced by rarity (rarity.json).
 3. Byproduct-only materials (a dust only met as a chanced byproduct of ore processing, which the mapper never
    values) and materials nothing makes get their rarity price on their dust.
 4. Items still at 0 that a recipe makes, but that ProjectE can't map (crafting with a GT tool, which only loses
    durability; GT tools; outputs with data components; decompositions, recycling, byproducts), are pinned at that
    recipe's ingredient cost, one step at a time, so that everything made from them is still derived. Pins the game
    can derive by itself are dropped. Items the game would floor to 0 (below 1 EMC) are pinned at 1.
 5. Every other fluid is listed at the value the mapper derives for it; listing changes how the mapper treats
    byproducts, so the items are priced again and fluids a recipe now makes for less are lowered, until none is.
    A filled bucket is pinned at the empty bucket plus its fluid.
"""
import json, math, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from emcmodel import Model, load_dump, _lines  # noqa: E402
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
VANILLA_NUGGETS_UNITS = {'minecraft:gold_nugget': ('gold', 1 / 9), 'minecraft:iron_nugget': ('iron', 1 / 9)}
WATER_FORMS = {'gtceu:distilled_water': 1, 'gtceu:ice': 1}
# A listed fluid a recipe makes for this much less is lowered (well under the 100 EMC exploit threshold; a smaller
# margin chases rounding around recipe cycles without settling).
LOWER_MARGIN = 50
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
        self.log_path = log
        # what the dumped game had listed (FLUIDDUMP's value), to tell whether its exploit warnings still apply
        self.listed_in_dump = {f: v[1] for f, v in self.dump[1].items() if f == v[0]}
        caps = os.path.join(HERE, 'game_caps.json')
        gc = json.load(open(caps)) if os.path.exists(caps) else {}
        self.game_caps = gc.get('caps', {})
        self.item_caps = gc.get('material_units', {})
        self.metal_mismatch = set(gc.get('dust_ingot', []))
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
        self.game_zero = set(json.load(open(zf))['items']) if os.path.exists(zf) else set()
        self.game_zero |= {k for k, v in self.items.items() if v == 0}  # filtered to what the model values in run()
        self.listed = dict(self.hand['fluids'])
        self.pins = {}  # item -> (value, reason)
        self.fluid_reasons = {}
        self.log = []

    # ---- helpers ----
    def models(self):
        self.game = Model(self.dump, self.listed, 'game', self.jar)
        self.cost = Model(self.dump, self.listed, 'cost', self.jar)
        # ProjectE's defaults for GT items (its metal and gem tags) are dropped: GT-mined materials are priced by
        # rarity and recipes (#59); override_pins() pins what they get instead.
        self.overridden = {k for k in self.game.fixed if k.startswith('i:gtceu:') and re.search(r'_(ingot|gem)$', k)}
        for m in (self.game, self.cost):
            for k in self.overridden:
                m.fixed.pop(k, None)
        self.cost_groups = defaultdict(list)
        for out, _, ing, src in self.cost.conv:
            if src == 'group':
                self.cost_groups[out].append(next(iter(ing)))

    def fixed(self):
        f = dict(self.game.fixed)
        f.update({'i:' + k: v for k, v in self.hand['items'].items()})
        f.update({'i:' + k: v for k, (v, _) in self.pins.items()})
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

    def game_item_caps(self, log):
        """ProjectE's own "EMC Exploit" warnings in the dump for a material's own forms: the game found a route to it
        cheaper than its unit (U-238 from depleted uranium hexafluoride, salt from sodium and chlorine). {material:
        unit cap}; material_units() lowers the unit to it, and game_caps.json keeps the cap."""
        caps = {}
        pat = re.compile(r'EMC Exploit: ingredients \(.* => (\d+)\*(minecraft:item: |NSSFake: \S+/fluid )(\S+)\) '
                         r'cost (\d+) but output value is (\d+)')
        for line in _lines(log):
            m = pat.search(line)
            if not m or int(m.group(5)) - int(m.group(4)) < LOWER_MARGIN:
                continue
            # a metal's molten fluid: 1000 mB is 1000/144 units
            u = mat_unit(m.group(3)) if m.group(2).startswith('minecraft') else (
                (m.group(3)[6:], 1000 / 144) if m.group(3).startswith('gtceu:') and m.group(3)[6:] in self.rarity else None)
            if not u or u[0] in self.floors or u[0] in PE_KEPT or any(
                    'gtceu:%s_%s' % (u[0], f) in self.hand['items'] for f in ('ingot', 'dust')):
                continue
            caps[u[0]] = min(caps.get(u[0], 1e18), int(m.group(4)) / (int(m.group(1)) * u[1]))
        return caps

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
            if m in self.item_caps and self.item_caps[m] < v:
                v, w = self.item_caps[m], 'game route cost'
            if self.floors.get(m, 0) > v:
                v, w = self.floors[m], 'late-tier floor'
            units[m] = (max(1, math.floor(v)), w)
        self.units = units
        self.recipe_consistency()
        self.alloy_units(val)
        for v, w in self.units.values():
            why[w] += 1
        self.log.append('material units: %s' % dict(why))

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
                            cost += self.listed.get(f, 0) * x['n'] / 1000
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
        """Pin each material's dust and gem at its unit value, and its ingot (dust = ingot: smelting one into the
        other neither gains nor loses), overriding ProjectE's tag defaults for GT-mined metals."""
        n = 0
        for m, (v, w) in sorted(self.units.items()):
            if m in PE_KEPT and w == 'ProjectE default':
                # vanilla metals: GT's dust, plate and nugget follow the ingot
                if m not in ('iron', 'gold', 'copper'):
                    for form, k in (('gtceu:%s_dust' % m, 1), ('gtceu:small_%s_dust' % m, 1 / 4),
                                    ('gtceu:tiny_%s_dust' % m, 1 / 9)):
                        if form in self.items and v * k >= 2 and self.pin(form, math.floor(v * k), 'form of %s' % PE_KEPT[m]):
                            n += 1
                    continue
                for form, k in (('gtceu:%s_dust' % m, 1), ('gtceu:%s_plate' % m, 1), ('minecraft:%s_nugget' % m, 1 / 9),
                                ('gtceu:%s_nugget' % m, 1 / 9)):
                    if form in self.items and self.pin(form, math.floor(v * k), 'form of %s (ProjectE default)' % PE_KEPT[m]):
                        n += 1
                continue
            for form in ('gtceu:%s_dust' % m, 'gtceu:%s_gem' % m, 'gtceu:%s_ingot' % m):
                if form in self.items and self.pin(form, v, '%s: %s' % (w, m)):
                    n += 1
            # the smaller and bigger forms follow (a nugget or tiny dust made from a cheap fluid would otherwise
            # turn back into a full-price ingot)
            for form, k in (('gtceu:%s_nugget' % m, 1 / 9), ('gtceu:tiny_%s_dust' % m, 1 / 9),
                            ('gtceu:small_%s_dust' % m, 1 / 4), ('gtceu:hot_%s_ingot' % m, 1), ('gtceu:%s_plate' % m, 1)):
                if form in self.items and v * k >= 2 and self.pin(form, math.floor(v * k), '%s form of %s' % (w, m)):
                    n += 1
        self.log.append('material dusts, gems and ingots pinned at their unit value: %d' % n)

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
                            tot += self.listed.get(f, 0) * x['n'] / 1000 * x['ch'] / x['mx']
                    for x in r.get('fi', []):
                        if x['ch'] > 0 and x['ids']:
                            f = self.fluids.get(x['ids'][0], (x['ids'][0],))[0]
                            tot -= self.listed.get(f, 0) * x['n'] / 1000
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

    FLOOR_FORMS = {'dust': 1, 'ingot': 1, 'gem': 1, 'hot_ingot': 1, 'plate': 1, 'nugget': 1 / 9, 'tiny_dust': 1 / 9,
                   'small_dust': 1 / 4, 'block': 9}

    def floor_pins(self, val):
        """Late-tier floors (owner decision 3, #59): each listed material's dust and ingot is worth at least its
        floor, so the tiers that need it take 5-10 Prestiges (prestiges_per_tier.py). Products derive upward."""
        n = []
        for m, f in sorted(self.floors.items()):
            for suffix, k in self.FLOOR_FORMS.items():
                prefix = suffix.split('_')[0] + '_' if suffix in ('hot_ingot', 'tiny_dust', 'small_dust') else ''
                form = 'gtceu:%s%s_%s' % (prefix, m, suffix.split('_')[-1])
                if form in self.items and self.pin(form, math.ceil(max(f * k, val.get('i:' + form, 0))),
                                                   'late-tier floor: %s' % m):
                    n.append(form)
        self.log.append('late-tier floors pinned: %d' % len(n))

    def override_pins(self, val):
        """GT items ProjectE's own defaults pin (its metal tags: tin, lead, silver, nickel, osmium, platinum, bronze
        ingots; ruby and sapphire gems) are priced like every other GT material (#59): the model drops ProjectE's
        value, and the file pins what the model gives them instead."""
        n = 0
        for k in sorted(self.overridden):
            item = k[2:]
            if item in self.pins:
                continue
            dust = re.sub(r'_(ingot|gem)$', '_dust', k)
            v = val.get(dust) or val.get(k)
            if v and self.pin(item, max(1, math.floor(v)), 'overrides ProjectE\'s default: derived value'):
                n += 1
        # ProjectE's tag node keeps its default too (a tag ingredient would value the item at it): pin the tag
        self.tag_pins = {}
        for t, ids in self.tags.items():
            if t.startswith(('c:ingots/', 'c:gems/')) and ids and all('i:' + i in self.overridden for i in ids):
                v = self.pins.get(ids[0], (None,))[0]
                if v:
                    self.tag_pins[t] = v
        self.log.append('ProjectE defaults overridden at their derived value: %d (tags %s)' % (n, ' '.join(sorted(self.tag_pins))))

    def metal_pins(self, val):
        """Each GT material's dust and ingot are worth the same (#59): where the model still derives them more than
        rounding apart (an ingot made through a machine that adds a little, a dust from a cheaper side route), the
        cheaper one is pinned at the other's value."""
        n = []
        for item in sorted(self.items):
            if not (item.startswith('gtceu:') and item.endswith('_ingot')) or item.startswith('gtceu:hot_'):
                continue
            dust = item[:-6] + '_dust'
            i, d = val.get('i:' + item), val.get('i:' + dust)
            gi, gd = self.items.get(item, 0), self.items.get(dust, 0)
            if not i or not d:
                continue
            m = item[6:-6]
            if m not in self.units and m not in self.floors and item not in self.pins and dust not in self.pins:
                # A metal the model derives (titanium, iridium, osmiridium): its dust and ingot are pinned at the
                # cheaper of the game's and the model's ingot, the value its molten fluid is listed at, so its parts
                # (cast from the fluid, or bent and turned from the ingot) and the fluid agree.
                v = min(x for x in (gi, i) if x)
                for form in (item, dust):
                    if self.pin(form, max(1, math.floor(v)), 'dust = ingot = its fluid'):
                        n.append(form)
                continue
            if gi and gd and abs(gi - gd) > max(1, 0.005 * max(gi, gd)):
                self.metal_mismatch.add(item)  # kept in game_caps.json: once pinned, the dump shows them equal
            if abs(i - d) <= max(1, 0.005 * max(i, d)) and item not in self.metal_mismatch:
                continue
            # the game's mapper (v0.3.0's output shares) can still split them: pin both, and the nugget
            for form in (item, dust):
                if self.pin(form, math.floor(max(i, d)), 'dust = ingot'):
                    n.append(form)
            nugget = item[:-6] + '_nugget'
            if nugget in self.items and nugget not in self.pins and self.pin(nugget, math.floor(max(i, d) / 9), 'dust = ingot'):
                n.append(nugget)
        self.log.append('dusts or ingots pinned to match the other: %d' % len(n))

    def game_zero_pins(self, val):
        """Items the game floors to 0 although this model values them (v0.3.0's output shares can price a tiny dust
        below 1 EMC): game_zero.json keeps every one a dump showed, pinned at the model's value (at least 1)."""
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
                bv = self.pins.get(big, (None,))[0] or val.get('i:' + big)
                if bv:
                    v = bv * k
            if v and self.pin(item, max(1, math.floor(v)), 'the game floors it to 0: pinned at its model value'):
                n += 1
        self.log.append('items the game floors to 0, pinned: %d' % n)

    def frontier(self, max_rounds=3000):
        """Pin items still at 0 at the ingredient cost of a recipe ProjectE can't map, one step at a time."""
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
                if out.startswith('f:'):
                    self.derived[out[2:]] = v
                    self.listed[out[2:]] = v
                    self.fluid_reasons[out[2:]] = 'ingredient cost of %s' % src
                else:
                    self.pin(out[2:], v, 'ingredient cost of %s%s' % (src, ' (below 1 EMC, rounded up)' if cost < 1 else ''))
            total += len(new)
        self.log.append('items pinned at a recipe\'s ingredient cost: %d in %d rounds' % (total, rnd + 1))

    def _group_value(self, val, g):
        vs = [val[m] for m in self.cost_groups.get(g, ()) if m in val]
        return min(vs) if vs else None

    def source_fluids(self):
        return sorted({v[0] for v in self.fluids.values()} - {'minecraft:empty'})

    def fluid_values(self, val):
        """List every fluid that isn't hand-set or free at the value the mapper derives for it while it is unlisted
        (or the fallback cost frontier() gave it), so the Prestige mod sees it at runtime."""
        new, unvalued = {}, []
        for f in self.source_fluids():
            if f in self.base_listed:
                continue
            v = val.get('f:' + f)
            if v is None:
                unvalued.append(f)
                continue
            new[f] = max(1, math.floor(v + 1e-9))
            self.fluid_reasons.setdefault(f, 'derived by the mapper')
        self.unvalued_fluids = unvalued
        return new

    def game_exploit_ratios(self, log):
        """ProjectE's own "EMC Exploit" warnings in the dump's log, for listed fluids: the game sometimes finds a
        route slightly cheaper than this model. {fluid: cost / value} for each warning gaining LOWER_MARGIN or more;
        run() caps the fluid at its dumped value times that ratio, and game_caps.json keeps the cap."""
        ratios = {}
        pat = re.compile(r'=> \d+\*NSSFake: mcincremental_prestige:gt_recipes/fluid (\S+)\) cost (\d+) but output value is (\d+)')
        for line in _lines(log):
            m = pat.search(line)
            if m and int(m.group(3)) - int(m.group(2)) >= LOWER_MARGIN:
                f, r = m.group(1), int(m.group(2)) / int(m.group(3))
                ratios[f] = min(r, ratios.get(f, 1))
        return ratios

    def lower_fluids(self):
        """Once listed, a fluid is a fixed value, and the mapper subtracts it from recipes that make it as a byproduct,
        which makes some routes cheaper. Lower any listed fluid that a recipe now makes for less (an exploit otherwise)."""
        val = self.solve()
        lowered = 0
        for out, cnt, ing, src in self.game.conv:
            f = out[2:]
            if not out.startswith('f:') or f not in self.derived or not ing or f in getattr(self, 'unit_fluids', ()):
                continue
            try:
                tot = sum(a * val[k] for k, a in ing.items())
            except KeyError:
                continue
            cost = tot / cnt
            if 1 <= cost < self.derived[f] - LOWER_MARGIN:
                self.derived[f] = max(1, math.floor(cost))
                lowered += 1
        self.log.append('listed fluids lowered to a cheaper recipe: %d' % lowered)
        return lowered

    def bucket_pins(self, val):
        empty = val.get('i:' + BUCKET)
        n = 0
        for f, (src, _, bucket) in self.fluids.items():
            if f != src or self.listed.get(f) is None:
                continue
            if bucket and bucket not in (BUCKET, 'minecraft:air') and self.pin(bucket, empty + self.listed[f], 'empty bucket + %s' % f):
                n += 1
        self.log.append('filled buckets pinned: %d' % n)

    def plasma_floor(self):
        """A metal's plasma is worth at least its molten fluid (a plasma cools into it)."""
        for f in list(self.derived):
            base = f[:-len('_plasma')] if f.endswith('_plasma') else None
            if base in self.unit_fluids and self.derived[f] < self.derived[base]:
                self.derived[f] = self.derived[base]
                self.fluid_reasons[f] = 'at least its molten fluid'

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
            # stays pinned on the next run, whose dump shows it at its pin.
            def is_low(k, v):
                g = self.items.get(k[2:])
                return v < 5 or (g is not None and g <= 2 and v < 20)
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

    PRUNABLE = ('ingredient cost', 'unobtainable', 'cheapest recipe')

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
        self.override_pins(self.solve())
        self.metal_pins(self.solve())
        self.cycle_pins(self.solve())
        self.game_zero_pins(self.solve())
        self.sub_unit()

    def run(self, max_lowering=20):
        """Pass 1 prices items with only the hand-set and free fluids listed, and lists every other fluid at the
        value the mapper gives it while unlisted. Listing changes how the mapper treats recipes that make those
        fluids as byproducts, so pass 2 prices the items again with every fluid listed, and listed fluids that a
        recipe now makes for less are lowered (and the items re-priced) until none is."""
        for m, cap in self.game_item_caps(self.log_path).items():
            self.item_caps[m] = math.floor(min(cap, self.item_caps.get(m, cap)))
        self.free_fluids()
        self.base_listed = dict(self.listed)
        self.game_zero = {k for k in self.game_zero if k in self.items and k != 'minecraft:air'}
        self.derived = {}
        self.one_pass()
        self.derived = self.fluid_values(self.solve())
        # A metal's molten fluid follows its unit (144 mB per ingot), so blocks, plates and parts cast from it don't
        # undercut the ingot; the game's caps and the lowering below leave these alone.
        self.unit_fluids = set()
        for m, (u, w) in self.units.items():
            f = 'gtceu:' + m
            if f in self.derived and ('gtceu:%s_ingot' % m in self.items or m in ('iron', 'gold', 'copper')):
                self.derived[f] = math.ceil(u * 1000 / 144)
                self.fluid_reasons[f] = '%s unit, 144 mB per ingot' % m
                self.unit_fluids.add(f)
        # Every other metal's molten fluid follows its ingot too (an alloy's parts melt into their fluid in an
        # extractor, so a fluid listed above the ingot would gain): the game's ingot value where the dump has it.
        val = self.solve()
        for f in list(self.derived):
            if f in self.unit_fluids or not f.startswith('gtceu:'):
                continue
            ingot = '%s_ingot' % f
            ivs = [v for v in (self.items.get(ingot), val.get('i:' + ingot)) if v]
            iv = min(ivs) if ivs else None  # the cheaper of the game's and the model's ingot
            if iv and ingot in self.items:
                self.derived[f] = max(1, math.ceil(iv * 1000 / 144))
                self.fluid_reasons[f] = 'its ingot, 144 mB per ingot'
                self.unit_fluids.add(f)
        self.plasma_floor()
        for m, f in self.floors.items():  # a floored material's molten fluid: 144 mB per ingot
            if 'gtceu:' + m in self.derived and self.derived['gtceu:' + m] < f * 1000 / 144:
                self.derived['gtceu:' + m] = math.ceil(f * 1000 / 144)
                self.unit_fluids.add('gtceu:' + m)
                self.fluid_reasons['gtceu:' + m] = 'late-tier floor (144 mB per ingot)'
        # Caps from ProjectE's own exploit warnings (game_caps.json keeps them, so a re-run from a dump of the capped
        # game, which no longer warns, gives the same values).
        for f, r in self.game_exploit_ratios(self.log_path).items():
            cap = math.floor(self.listed_in_dump.get(f, 0) * r)
            if cap >= 1:
                self.game_caps[f] = min(cap, self.game_caps.get(f, cap))
        for f, cap in self.game_caps.items():
            if f in self.derived and cap < self.derived[f] and f not in self.unit_fluids:
                self.derived[f] = cap
                self.log.append('capped %s at the cheaper route ProjectE found in the game' % f)
        for _ in range(max_lowering):
            self.listed = dict(self.base_listed, **self.derived)
            self.one_pass()
            lowered = self.lower_fluids()
            self.plasma_floor()  # fluids frontier() lists on the way (a plasma nothing else values)
            if not lowered:
                break
        self.listed = dict(self.base_listed, **self.derived)
        self.models()
        self.bucket_pins(self.solve())
        self.log.append('fluids no recipe makes (allow-listed): %s' % ' '.join(self.unvalued_fluids))
        return self.solve()


CUSTOM_EMC_COMMENT = (
    "Mc-incremental EMC values (#41, #47, #55). GENERATED by docs/research/emc-pricing/generate.py from "
    "hand_values.json, rarity.json and ore_yields.json there: do not edit by hand, edit those and re-run it. "
    "ProjectE applies this file after its datapack defaults, so these values win. It holds only what neither ProjectE "
    "nor the Prestige mod's GT recipe mapper (#52) can derive: hand values (steam-age parts, vanilla items GT hides "
    "from ProjectE, obtainable items no recipe makes), every ore block and raw ore (worth what fully processing it "
    "yields), the dusts of materials only ever met as byproducts (priced by rarity), items whose only recipes ProjectE "
    "can't map (crafting with a GT tool, decompositions; pinned at that recipe's ingredient cost) and filled buckets "
    "(empty bucket + fluid). The Transmutation Tablet is 0: the Prestige mod hands it out. See docs/pocs/poc-1.md.")
FLUIDS_COMMENT = (
    "EMC per 1000 mB of each fluid, for the Prestige mod (ProjectE can't hold fluid values) and its GT recipe mapper. "
    "GENERATED by docs/research/emc-pricing/generate.py: edit hand_values.json there and re-run it. Water is the one "
    "free fluid. Lava is ProjectE's default lava bucket minus the empty bucket; GT fuels are hand-set; fluids GT makes "
    "from water and air alone are a nominal 1; every other fluid is listed at the value the mapper derives for it "
    "from its recipes. A filled bucket is worth the empty bucket plus its fluid (custom_emc.json).")


def write(g):
    entries = dict(g.hand['items'])
    entries.update({k: v for k, (v, _) in g.pins.items()})
    lines = ['  {"id": %s, "emc": %d}' % (json.dumps(k), v) for k, v in sorted(entries.items())]
    # Tags ProjectE's own defaults pin that must follow an item's new value (owner decision 5: c:nether_stars).
    tags = dict(g.hand.get('tags', {}).get('tags', {}))
    tags.update(g.tag_pins)
    lines += ['  {"tag": %s, "emc": %d}' % (json.dumps(k), v) for k, v in sorted(tags.items())]
    with open(CUSTOM_EMC, 'w') as f:
        f.write('{\n "comment": %s,\n "entries": [\n%s\n ]\n}\n' % (json.dumps(CUSTOM_EMC_COMMENT), ',\n'.join(lines)))
    fl = ['  %s: %d' % (json.dumps(k), v) for k, v in sorted(g.listed.items())]
    with open(FLUIDS, 'w') as f:
        f.write('{\n "comment": %s,\n "emc_per_1000_mb": {\n%s\n }\n}\n' % (json.dumps(FLUIDS_COMMENT), ',\n'.join(fl)))
    zero = sorted(k for k, (_, why) in g.pins.items() if why.startswith('the game floors it to 0'))
    with open(os.path.join(HERE, 'game_zero.json'), 'w') as f:
        json.dump({'comment': 'Generated by generate.py: items a dump showed at 0 EMC although the model values them '
                              '(the game floors them), pinned at their model value. Kept so re-runs are stable.',
                   'items': zero}, f, indent=1)
        f.write('\n')
    with open(os.path.join(HERE, 'game_caps.json'), 'w') as f:
        json.dump({'comment': 'Generated by generate.py: listed fluids (caps, EMC per 1000 mB) and material units '
                              '(material_units, EMC per dust) capped at a cheaper route ProjectE found in the game (its '
                              '"EMC Exploit" warnings in a dump). Kept so re-runs are stable.',
                   'caps': dict(sorted(g.game_caps.items())),
                   'material_units': dict(sorted(g.item_caps.items())),
                   'dust_ingot': sorted(g.metal_mismatch)}, f, indent=1)
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
