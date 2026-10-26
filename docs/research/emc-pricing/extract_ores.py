"""Blocks per Run area, by dimension, from the research dumps (docs/research/emc-economy.md, dimensions.md).

Usage: python3 extract_ores.py OW_DUMP... --nether-end DIMS_CONSOLE > ore_counts.json

- OW_DUMP: logs from emc-economy/zz_econ.js; every `[ECON] AREA <name> <x> {block: count}` line is one 3x3-chunk Run
  area (124 areas over two seeds).
- DIMS_CONSOLE: the console of the dimensions research server (zz_dims.js); every `[DIMS] NETHER ... C={...}` line is
  one 48x48 Nether area (40), every `[DIMS] END ... C={...}` line one 3x3-chunk End area (30).

A Run lies wholly in one dimension (ADR-0008), so each dimension's areas are one kind of Run. End Run areas lie only
on islands with enough land, so End areas with fewer than END_LAND_MIN end stone blocks are left out (as the
overworld's ocean areas would be; those are kept here, as in the research).

Writes, per dimension, the mean count per area of every ore block (ids ending in `_ore`, plus ancient debris) and of
every other block (except air, fluids and bedrock). The raw dumps are not committed (regenerate them with the
research scripts); this output is.
"""
import json, re, sys
from collections import Counter

END_LAND_MIN = 10000
SKIP = {'minecraft:air', 'minecraft:cave_air', 'minecraft:void_air', 'minecraft:water', 'minecraft:lava',
        'minecraft:bedrock'}


def is_ore(block):
    return block.endswith('_ore') or block == 'minecraft:ancient_debris'


def main(argv):
    if '--nether-end' not in argv:
        sys.exit(__doc__)
    i = argv.index('--nether-end')
    ow_files, dims_file = argv[:i], argv[i + 1]
    dims = {'overworld': [], 'the_nether': [], 'the_end': []}
    for f in ow_files:
        for line in open(f, encoding='utf-8', errors='replace'):
            if line.startswith('[ECON] AREA '):
                dims['overworld'].append(json.loads(line.split(' ', 4)[4]))
    for line in open(dims_file, encoding='utf-8', errors='replace'):
        m = re.search(r'\[DIMS\] (NETHER|END) .*? C=(\{.*\})\s*$', line)
        if m:
            dims['the_nether' if m.group(1) == 'NETHER' else 'the_end'].append(json.loads(m.group(2)))
    sampled = len(dims['the_end'])
    dims['the_end'] = [a for a in dims['the_end'] if a.get('minecraft:end_stone', 0) >= END_LAND_MIN]
    out = {}
    for dim, areas in dims.items():
        tot = Counter()
        for a in areas:
            tot.update(a)
        mean = lambda pred: {b: round(n / len(areas), 2) for b, n in sorted(tot.items())
                             if pred(b) and b not in SKIP and n / len(areas) >= 0.01}
        out[dim] = {'areas': len(areas), 'mean_ore_blocks': mean(is_ore),
                    'mean_other_blocks': mean(lambda b: not is_ore(b))}
    out['the_end']['comment'] = '%d of %d sampled End areas hold at least %d end stone' % (
        len(dims['the_end']), sampled, END_LAND_MIN)
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main(sys.argv[1:])
