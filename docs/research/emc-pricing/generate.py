"""Generate the Pack's EMC values (VexedPanda/Mc-incremental#55): pack/config/ProjectE/custom_emc.json and
pack/kubejs/data/mcincremental_prestige/fluid_emc/fluids.json.

Usage:
  python3 generate.py SERVER_LOG PROJECTE_JAR [--write]

SERVER_LOG is the console of a smoke-test server run with dump.js added (see README.md); PROJECTE_JAR is the ProjectE
jar from that server's mods/ (its default values). Without --write it only prints the report.

What it does, in order (emcmodel.py replays ProjectE and the Prestige mod's GT recipe mapper offline):
 1. Fixed values: ProjectE's defaults, plus hand_values.json (steam-age pins, vanilla items GT hides from ProjectE,
    obtainable items no recipe makes, the fuels and the free fluids).
 2. Byproduct-only materials (a dust or gem that only turns up as a chanced byproduct of ore processing, which the
    mapper never values) get their rarity price (rarity.json) on their dust or gem.
 3. Every ore block and raw ore is worth what fully processing it yields (ore_yields.json): its crushed ores' unit
    plus the expected byproducts. A material's unit is the value its dust or gem already has, at least what smelting
    it gives (goethite dust smelts to an iron ingot); a material with neither is priced by rarity.
 4. Items still at 0 that a recipe makes, but that ProjectE can't map (crafting with a GT tool, which only loses
    durability, or making one), are pinned at that recipe's ingredient cost, one recipe step at a time, so that
    everything made from them is still derived. A cost below 1 EMC is pinned at 1 (ProjectE has no fractions).
 5. Every fluid is listed at the value the mapper derives for it; a filled bucket is pinned at the empty bucket plus
    its fluid.
"""
import json, math, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from emcmodel import Model, load_dump  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CUSTOM_EMC = os.path.join(REPO, 'pack', 'config', 'ProjectE', 'custom_emc.json')
FLUIDS = os.path.join(REPO, 'pack', 'kubejs', 'data', 'mcincremental_prestige', 'fluid_emc', 'fluids.json')
VANILLA_UNITS = {'redstone': 'minecraft:redstone', 'diamond': 'minecraft:diamond', 'emerald': 'minecraft:emerald',
                 'coal': 'minecraft:coal', 'lapis': 'minecraft:lapis_lazuli', 'nether_quartz': 'minecraft:quartz',
                 'amethyst': 'minecraft:amethyst_shard', 'flint': 'minecraft:flint',
                 'glowstone': 'minecraft:glowstone_dust'}
BUCKET = 'minecraft:bucket'
NOMINAL = 1  # EMC per 1000 mB of a fluid made from water and air alone


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
        self.ores, self.crushed = y['ores'], y['crushed']
        self.listed = dict(self.hand['fluids'])
        self.pins = {}  # item -> (value, reason)
        self.fluid_reasons = {}
        self.log = []

    # ---- helpers ----
    def models(self):
        self.game = Model(self.dump, self.listed, 'game', self.jar)
        self.cost = Model(self.dump, self.listed, 'cost', self.jar)
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
    def byproduct_materials(self, val):
        primaries = {c[0][0] for c in self.crushed.values()}
        mats = set()
        for _, _, byp in self.ores.values():
            mats.update(byp)
        for _, byp in self.crushed.values():
            mats.update(byp)
        n = 0
        for m in sorted(mats - primaries):
            if self.unit_value(val, m) > 0 or m not in self.rarity:
                continue
            item = next((i for i in unit_items(m) if i in self.items), None)
            if item and self.pin(item, self.rarity[m], 'rarity: byproduct-only material %s' % m):
                n += 1
        self.log.append('byproduct-only materials priced by rarity: %d' % n)

    def smelt_floor(self, val, item):
        best = 0
        for r in self.recipes:
            if r['type'] in ('minecraft:smelting', 'minecraft:blasting') and r['o'] and any(item in x['ids'] for x in r['i']):
                o = r['o'][0]
                best = max(best, val.get('i:' + o['ids'][0], 0) * o['n'])
        return best

    def ore_units(self, val):
        units = {}
        for mat, ((unit, amount), _) in self.crushed.items():
            item = next((i for i in unit_items(unit) if i in self.items), None)
            v = self.unit_value(val, unit)
            floor = self.smelt_floor(val, item) if item else 0
            if max(v, floor) > 0:
                units[unit] = (max(v, floor), 'unit value' if v >= floor else 'smelting floor')
            else:
                # priced by rarity; a material no Run turns up (its ore never generates) at the rarity cap
                units[unit] = (self.rarity.get(unit, max(self.rarity.values())), 'rarity')
        self.units = units
        c = defaultdict(int)
        for _, why in units.values():
            c[why] += 1
        self.log.append('ore material units: %s' % dict(c))

    def ore_pins(self, val):
        def v(m):
            if m in self.units:
                return self.units[m][0]
            return self.unit_value(val, m)

        n = 0
        for block, (mat, count, byp) in sorted(self.ores.items()):
            (unit, amount), route = self.crushed[mat]
            if unit not in self.units:
                self.log.append('ore without a unit value: %s (%s)' % (block, unit))
                continue
            value = count * (v(unit) * amount + sum(n_ * v(m) for m, n_ in route.items()))
            value += sum(n_ * v(m) for m, n_ in byp.items())
            if self.pin(block, math.ceil(value), 'ore yield: %g crushed %s' % (count, mat)):
                n += 1
        self.log.append('ore blocks and raw ores pinned: %d' % n)

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
        """List every other fluid at the value the mapper derives for it, so the Prestige mod sees it at runtime."""
        unvalued = []
        for f in self.source_fluids():
            if f in self.listed:
                continue
            v = val.get('f:' + f)
            if v is None:
                unvalued.append(f)
                continue
            self.listed[f] = max(1, math.floor(v + 1e-9))
            self.fluid_reasons[f] = 'derived by the mapper'
        self.unvalued_fluids = unvalued
        self.log.append('fluids listed at their derived value: %d; still unvalued: %s' % (
            sum(1 for r in self.fluid_reasons.values() if r == 'derived by the mapper'), ' '.join(unvalued)))

    def bucket_pins(self, val):
        empty = val.get('i:' + BUCKET)
        n = 0
        for f, (src, _, bucket) in self.fluids.items():
            if f != src or self.listed.get(f) is None:
                continue
            if bucket and bucket not in (BUCKET, 'minecraft:air') and self.pin(bucket, empty + self.listed[f], 'empty bucket + %s' % f):
                n += 1
        self.log.append('filled buckets pinned: %d' % n)

    FREE_FLUIDS = ('minecraft:water',)

    def free_fluids(self):
        """Fluids GT makes from water and air alone (gas collectors, distillation, electrolysis and the chemistry
        on top of them, with no item consumed): they cost nothing but energy, so they get a nominal value."""
        free = {'f:' + f for f in self.FREE_FLUIDS}
        src = lambda i: 'f:' + self.fluids.get(i, (i,))[0]
        changed = True
        while changed:
            changed = False
            for r in self.recipes:
                if not r.get('gt') or (r.get('cat') or '').endswith('_recycling'):
                    continue
                if any(x['ch'] > 0 and x.get('cu') != 'IntCircuitIngredient' for x in r['i']):
                    continue
                if not all(any(src(i) in free for i in x['ids']) for x in r['fi'] if x['ch'] > 0):
                    continue
                for x in r['fo']:
                    if x['ch'] >= x['mx'] and len(x['ids']) == 1 and src(x['ids'][0]) not in free:
                        free.add(src(x['ids'][0]))
                        changed = True
        n = 0
        for f in sorted(free):
            if f[2:] not in self.hand['fluids']:
                self.listed[f[2:]] = NOMINAL
                n += 1
        self.log.append('fluids made from water and air alone, at a nominal %d EMC: %d' % (NOMINAL, n))

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
        from 1-EMC stone, glass from sand and a whiff of oxygen) ends up at 0. Pin those at 1 (and those below 2,
        which the game may cost slightly lower, at their floor)."""
        n = 0
        for _ in range(20):
            val = self.solve()
            # Below 2, not 1: the game sometimes finds a slightly cheaper route than this model does. When the dump
            # was taken from a server running these values, an item it shows at 2 or less that this model costs under
            # 20 EMC is rounding too (its base is cheaper in the game, e.g. tiny silicon dust from 8-EMC silicon); it
            # stays pinned on the next run, whose dump shows it at its pin.
            def is_low(k, v):
                g = self.items.get(k[2:])
                return v < 2 or (g is not None and g <= 2 and v < 20)
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

    def run(self):
        self.free_fluids()
        self.models()
        val = self.solve()
        self.byproduct_materials(val)
        val = self.solve()
        self.ore_units(val)
        self.ore_pins(val)
        self.frontier()
        self.fluid_values(self.solve())
        self.models()  # listed fluids change how the mapper treats byproducts
        self.frontier()
        self.unobtainable_materials(self.solve())
        self.frontier()
        self.fluid_values(self.solve())
        self.models()
        self.frontier()
        self.smelted_ores(self.solve())
        self.frontier()
        self.cycle_pins(self.solve())
        self.sub_unit()
        val = self.solve()
        self.bucket_pins(val)
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
    with open(CUSTOM_EMC, 'w') as f:
        f.write('{\n "comment": %s,\n "entries": [\n%s\n ]\n}\n' % (json.dumps(CUSTOM_EMC_COMMENT), ',\n'.join(lines)))
    fl = ['  %s: %d' % (json.dumps(k), v) for k, v in sorted(g.listed.items())]
    with open(FLUIDS, 'w') as f:
        f.write('{\n "comment": %s,\n "emc_per_1000_mb": {\n%s\n }\n}\n' % (json.dumps(FLUIDS_COMMENT), ',\n'.join(fl)))
    print('wrote %d item values to %s and %d fluid values to %s' % (len(lines), CUSTOM_EMC, len(fl), FLUIDS))


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    g = Generator(argv[0], argv[1])
    val = g.run()
    for l in g.log:
        print(l)
    zero = sorted(k for k in g.items if k != 'minecraft:air' and val.get('i:' + k, 0) < 1)
    print('items the model leaves at 0 (the smoke test allow-lists the unobtainable ones): %d' % len(zero))
    if '--write' in argv:
        write(g)
    if os.environ.get('GEN_OUT'):
        json.dump({'zero': zero, 'pins': g.pins, 'listed': g.listed,
                   'val': {k: v for k, v in val.items() if not k.startswith('g:')}}, open(os.environ['GEN_OUT'], 'w'))


if __name__ == '__main__':
    main(sys.argv[1:])
