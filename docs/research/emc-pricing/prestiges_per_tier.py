"""Prestiges needed to complete each GT tier (VexedPanda/Mc-incremental#59, owner decision 1).

Usage: python3 prestiges_per_tier.py [DUMP] [--model GEN_OUT.json] [--games N] > prestiges_per_tier.txt

The balancing metric: about 5-10 Prestiges per tier, counting the Runs spent discovering the tier's materials.

    Prestiges(tier) = discovery Runs(tier) + kit cost(tier) / net EMC per Run(tier)

- **Kit cost** is what the tier's kit is worth in game (EMCDUMP values from DUMP, by default the committed
  dump.txt.xz; or a generate.py GEN_OUT model with --model): KIT_MACHINES at the tier plus the tier's key multiblock
  (KIT_MULTIBLOCKS: EBF, vacuum freezer, large chemical reactor, assembly line, fusion reactors). The sweep refunds a
  kit at full value, so it is a float: one kit's worth of EMC has to be earned once per tier.
- **Net EMC per Run** is what one Run area yields when mined and banked, in the best Run dimension the world can
  reach while working towards the tier (DIMENSION_FROM): ORE_FRACTION of its ore blocks (the reach of the miner the
  previous tier has: GT's LV/MV/HV miners mine a radius of 8/16/24 blocks, so a 48x48 area is covered from HV) and
  ROCK_FRACTION of its other blocks (dug by hand; nothing in GT quarries rock), at their EMC (ore_counts.json).
- **Discovery Runs** come from a Monte Carlo game (GAMES games): each Run the players see 3 Candidate areas
  (ADR-0008) in a dimension they can reach, each with its veins drawn by GT's vein weights (VEINS, from
  docs/research/dimensions.md), pick the one that holds the most still-undiscovered sources the current tier needs
  (DISCOVERY), and discover everything their area holds (ADR-0009). A tier's discovery Runs are the Runs spent before
  all its sources are found; sources found by chance in earlier Runs cost nothing. Fusion products need no Run.

Every assumption is a named constant below; final balance comes from playtesting.
"""
import json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from emcmodel import load_dump  # noqa: E402

TIERS = ['lv', 'mv', 'hv', 'ev', 'iv', 'luv', 'zpm', 'uv']
TARGET = (5, 10)
KIT_MACHINES = ['macerator', 'assembler', 'circuit_assembler', 'chemical_reactor', 'electrolyzer', 'centrifuge',
                'cutter', 'laser_engraver', 'mixer', 'electric_furnace', 'wiremill', 'bender', 'lathe', 'extruder',
                'ore_washer', 'thermal_centrifuge']
# Key multiblock per tier: {item: count}; '{t}' is the tier. Block counts from GT's multiblock patterns (research).
KIT_MULTIBLOCKS = {
    'lv': {'electric_blast_furnace': 1, 'cupronickel_coil_block': 16, 'heatproof_machine_casing': 11,
           'lv_energy_input_hatch': 2, 'lv_input_bus': 1, 'lv_output_bus': 1, 'maintenance_hatch': 1,
           'lv_muffler_hatch': 1},
    'hv': {'vacuum_freezer': 1, 'frostproof_machine_casing': 22, 'hv_energy_input_hatch': 1, 'hv_input_bus': 1,
           'hv_output_bus': 1, 'maintenance_hatch': 1},
    'ev': {'large_chemical_reactor': 1, 'inert_machine_casing': 20, 'ev_energy_input_hatch': 1, 'ev_input_bus': 1,
           'ev_output_bus': 1, 'maintenance_hatch': 1},
    'iv': {'assembly_line': 1, 'solid_machine_casing': 13, 'ulv_input_bus': 5, 'laminated_glass': 10,
           'assembly_line_unit': 5, 'assembly_line_casing': 5, 'assembly_line_grating': 5, 'iv_energy_input_hatch': 2,
           'lv_output_bus': 1, 'data_access_hatch': 1, 'maintenance_hatch': 1},
    'luv': {'luv_fusion_reactor': 1, 'fusion_casing': 95, 'superconducting_coil': 4, 'luv_energy_input_hatch': 16,
            'luv_input_hatch': 2, 'luv_output_hatch': 1},
    'zpm': {'zpm_fusion_reactor': 1, 'fusion_casing_mk2': 95, 'fusion_coil': 4, 'zpm_energy_input_hatch': 16,
            'zpm_input_hatch': 2, 'zpm_output_hatch': 1},
    'uv': {'uv_fusion_reactor': 1, 'fusion_casing_mk3': 95, 'fusion_coil': 4, 'uv_energy_input_hatch': 16,
           'uv_input_hatch': 2, 'uv_output_hatch': 1},
}
# Share of a Run area's ore blocks mined while working towards each tier (the previous tier's reach: by hand and a
# steam miner for LV, the LV miner (17x17 of 48x48) for MV, the MV miner (33x33) for HV, the HV miner for the rest).
ORE_FRACTION = {'lv': 0.1, 'mv': 0.15, 'hv': 0.5, 'ev': 1.0, 'iv': 1.0, 'luv': 1.0, 'zpm': 1.0, 'uv': 1.0}
ROCK_FRACTION = 0.1
# The first tier worked towards from each Run dimension (Dimension gates: the Nether needs obsidian and flint and
# steel; the End an eye of ender, so blaze powder: a fortress blaze, or GT's HV chemical reactor).
DIMENSION_FROM = {'overworld': 'lv', 'the_nether': 'mv', 'the_end': 'ev'}
# GT vein weights per layer (docs/research/dimensions.md): a Run area holds one vein per layer.
VEINS = {
    'overworld': {
        'stone': {'iron': 14, 'cassiterite': 9.3, 'coal': 9.3, 'garnet_tin': 9.3, 'magnetite': 9.3,
                  'mineral_sand': 9.3, 'copper_tin': 5.8, 'salts': 5.8, 'apatite': 4.7, 'galena': 4.7,
                  'garnet': 4.7, 'lubricant': 4.7, 'nickel': 4.7, 'oilsands': 4.7},
        'deepslate': {'copper': 23.5, 'redstone': 17.6, 'sapphire': 17.6, 'diamond': 11.8, 'lapis': 11.8,
                      'manganese': 5.9, 'mica': 5.9, 'olivine': 5.9},
        'surface': {'emerald_mountains': 23, 'none': 77}},
    'the_nether': {
        'netherrack': {'sulfur': 100, 'nether_quartz': 80, 'tetrahedrite': 70, 'topaz': 70, 'nether_redstone': 60,
                       'certus_quartz': 40, 'saltpeter': 40, 'banded_iron': 30, 'beryllium': 30, 'monazite': 30,
                       'nether_manganese': 20, 'molybdenum': 5},
        'structure': {'fortress': 12.5, 'none': 87.5}},
    'the_end': {
        'endstone': {'end_bauxite': 40, 'end_magnetite': 30, 'naquadah': 30, 'pitchblende': 30, 'scheelite': 20,
                     'sheldonite': 10},
        'rock': {'end_stone': 100}},
}
# What each tier must discover first, and the veins (or structures) that hold each source (docs/research/dimensions.md:
# "Material -> first tier it appears in a machine bill", "Overworld materials that come from one vein only", and the
# gating materials).
DISCOVERY = {
    'lv': {'antimony': {'copper_tin', 'tetrahedrite'}},
    'mv': {'gallium': {'mica', 'end_bauxite'}, 'vanadium': {'magnetite', 'end_magnetite'}, 'boron': {'salts'},
           'emerald': {'emerald_mountains', 'beryllium'}},
    'hv': {'chromium': {'redstone', 'nether_redstone', 'end_magnetite'}, 'barium': {'copper_tin', 'certus_quartz'},
           'titanium': {'mica', 'end_bauxite'}, 'neodymium': {'monazite'}},
    'ev': {'molybdenum': {'molybdenum', 'scheelite'}, 'nether star': {'fortress'},
           'platinum': {'copper', 'nickel', 'sheldonite'}},
    'iv': {'tungsten': {'end_stone', 'scheelite'}, 'sphalerite (indium)': {'sulfur'}, 'galena (indium)': {'galena'}},
    'luv': {'naquadah (trinium)': {'naquadah'}},
    'zpm': {'beryllium': {'beryllium', 'emerald_mountains'}},
    'uv': {},
}
GAMES = 2000
CANDIDATES = 3


def load_values(argv):
    if '--model' in argv:
        g = json.load(open(argv[argv.index('--model') + 1]))
        return {k[2:]: v for k, v in g['val'].items() if k.startswith('i:')}, 'model ' + os.path.basename(
            argv[argv.index('--model') + 1])
    args = [a for a in argv if not a.startswith('--') and not a.isdigit()]
    path = args[0] if args else os.path.join(HERE, 'dump.txt.xz')
    return load_dump(path)[0], 'dump ' + os.path.basename(path)


def kit(values, t):
    items = {'gtceu:%s_%s' % (t, m): 1 for m in KIT_MACHINES}
    for k, n in KIT_MULTIBLOCKS.get(t, {}).items():
        items['gtceu:' + k] = items.get('gtceu:' + k, 0) + n
    missing = [i for i in items if not values.get(i)]
    return sum(n * values.get(i, 0) for i, n in items.items()), missing


def run_value(values, counts):
    """{dimension: (ore EMC, other blocks EMC)} per Run area."""
    out = {}
    for dim, d in counts.items():
        ore = sum(n * values.get(b, 0) for b, n in d['mean_ore_blocks'].items())
        other = sum(n * values.get(b, 0) for b, n in d.get('mean_other_blocks', {}).items())
        out[dim] = (ore, other)
    return out


def net_per_run(rv, t):
    reach = [d for d, first in DIMENSION_FROM.items() if TIERS.index(first) <= TIERS.index(t)]
    best = max(reach, key=lambda d: ORE_FRACTION[t] * rv[d][0] + ROCK_FRACTION * rv[d][1])
    return ORE_FRACTION[t] * rv[best][0] + ROCK_FRACTION * rv[best][1], best


def draw_area(rng, dim):
    found = set()
    for layer in VEINS[dim].values():
        names, weights = zip(*layer.items())
        found.add(rng.choices(names, weights)[0])
    return found


def discovery_runs(games, seed=59):
    rng = random.Random(seed)
    total = {t: 0 for t in TIERS}
    for _ in range(games):
        seen = set()
        for t in TIERS:
            dims = [d for d, first in DIMENSION_FROM.items() if TIERS.index(first) <= TIERS.index(t)]
            need = lambda: [srcs for srcs in DISCOVERY[t].values() if not srcs & seen]
            while need():
                cands = [draw_area(rng, d) for d in dims for _ in range(CANDIDATES)]
                best = max(cands, key=lambda a: sum(1 for srcs in need() if srcs & a))
                seen |= best
                total[t] += 1
    return {t: n / games for t, n in total.items()}


def main(argv):
    values, source = load_values(argv)
    games = int(argv[argv.index('--games') + 1]) if '--games' in argv else GAMES
    counts = json.load(open(os.path.join(HERE, 'ore_counts.json')))
    rv = run_value(values, counts)
    disc = discovery_runs(games)
    print('# Prestiges per tier (#59), from %s' % source)
    print()
    print('EMC per Run area when fully mined and banked (ores | other blocks | total):')
    for d, (o, b) in rv.items():
        print('  %-10s %12s | %12s | %12s' % (d, '{:,.0f}'.format(o), '{:,.0f}'.format(b), '{:,.0f}'.format(o + b)))
    print()
    print('| Tier | Kit cost | Net EMC/Run (dimension) | Kit Runs | Discovery Runs | Prestiges |')
    print('|---|---:|---|---:|---:|---:|')
    rows, prev, problems = [], 0, []
    for t in TIERS:
        k, missing = kit(values, t)
        net, dim = net_per_run(rv, t)
        p = disc[t] + k / net
        rows.append((t, k, net, dim, k / net, disc[t], p))
        print('| %s | %s | %s (%s) | %.1f | %.1f | **%.1f** |' % (
            t.upper(), '{:,.0f}'.format(k), '{:,.0f}'.format(net), dim, k / net, disc[t], p))
        if missing:
            problems.append('%s kit items with no EMC: %s' % (t.upper(), ', '.join(missing)))
        if k <= prev:
            problems.append('%s kit (%s) does not cost more than the tier below (%s)' % (
                t.upper(), '{:,.0f}'.format(k), '{:,.0f}'.format(prev)))
        prev = k
        if not TARGET[0] <= p <= TARGET[1]:
            problems.append('%s takes %.1f Prestiges, outside %d-%d' % (t.upper(), p, *TARGET))
    print()
    print('Invariants (kit cost rises with tier; %d-%d Prestiges per tier):' % TARGET)
    for p in problems or ['all hold']:
        print('- ' + p)
    print()
    print('Assumptions: ore fraction mined per tier %s; rock fraction %g; dimensions from %s; %d games, %d candidates.' % (
        ORE_FRACTION, ROCK_FRACTION, DIMENSION_FROM, games, CANDIDATES))


if __name__ == '__main__':
    main(sys.argv[1:])
