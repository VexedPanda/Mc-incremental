"""Ore blocks per Run area, by dimension, from the research dumps (docs/research/emc-economy.md, dimensions.md).

Usage: python3 extract_ores.py OW_DUMP... --nether-end DIMS_CONSOLE > ore_counts.json

- OW_DUMP: logs from emc-economy/zz_econ.js; every `[ECON] AREA <name> <x> {block: count}` line is one 3x3-chunk Run
  area (124 areas over two seeds).
- DIMS_CONSOLE: the console of the dimensions research server (zz_dims.js); every `[DIMS] NETHER ... C={...}` line is
  one 48x48 Nether area at a Run's scaled centre (40), every `[DIMS] END ... C={...}` line one End area (30).

Writes the mean count of every ore block (ids ending in `_ore`, plus ancient debris) per area of each dimension. The
raw dumps are not committed (regenerate them with the research scripts); this output is.
"""
import json, re, sys
from collections import Counter


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
    out = {}
    for dim, areas in dims.items():
        tot = Counter()
        for a in areas:
            for b, n in a.items():
                if is_ore(b):
                    tot[b] += n
        out[dim] = {'areas': len(areas), 'mean_ore_blocks': {b: round(n / len(areas), 2) for b, n in sorted(tot.items())}}
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main(sys.argv[1:])
