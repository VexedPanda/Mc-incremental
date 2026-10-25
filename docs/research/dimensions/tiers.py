exec(open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/dimana/report.py').read())

COMP = ['machine_hull', 'energy_input_hatch', 'electric_motor', 'electric_pump', 'conveyor_module', 'robot_arm', 'electric_piston',
        'emitter', 'sensor', 'field_generator', 'macerator', 'assembler', 'circuit_assembler', 'chemical_reactor', 'electrolyzer',
        'centrifuge', 'cutter', 'laser_engraver', 'mixer', 'electric_furnace']
TT = ['lv', 'mv', 'hv', 'ev', 'iv', 'luv', 'zpm', 'uv']
MULTI = ['gtceu:electric_blast_furnace', 'gtceu:vacuum_freezer', 'gtceu:large_chemical_reactor', 'gtceu:cleanroom',
         'gtceu:assembly_line', 'gtceu:luv_fusion_reactor', 'gtceu:zpm_fusion_reactor', 'gtceu:uv_fusion_reactor'] + \
        [f'gtceu:{c}_coil_block' for c in COILS]

def tier_report(R):
    rows = {}
    for t in TT:
        have = [c for c in COMP if f'gtceu:{t}_{c}' in R]
        miss = [c for c in COMP if f'gtceu:{t}_{c}' not in R and f'gtceu:{t}_{c}' in ALLITEMS | {f'gtceu:{t}_{x}' for x in COMP}]
        circ = bool(itags.get(f'gtceu:circuits/{t}', set()) & R)
        rows[t] = (len(have), miss, circ)
    return rows

def highest_full(R):
    best = 'steam'
    for t in TT:
        if f'gtceu:{t}_machine_hull' in R and f'gtceu:{t}_energy_input_hatch' in R and itags.get(f'gtceu:circuits/{t}', set()) & R:
            best = t
        else: break
    return best

def mats_present(R, F):
    out = set()
    for x in R | F:
        m = re.match(r'gtceu:([a-z0-9_]+?)_(ingot|dust|gem)$', x)
        if m: out.add(m.group(1))
        elif x.startswith('gtceu:') and x in F: out.add(x[6:])
    return out
