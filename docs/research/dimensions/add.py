exec(open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/dimana/knock.py').read().split("for name, items in KO.items()")[0])
OWD = {'minecraft:overworld'}
def summary(R):
    out = []
    for t in TT:
        n = sum(1 for c in COMP if f'gtceu:{t}_{c}' in R)
        out.append(f'{t}:{n}')
    return highest_full(R), ' '.join(out), [m.split(':')[1].replace('_coil_block','C').replace('_fusion_reactor','F') for m in MULTI if m in R]
R,F,_ = closure_m(OW, FL, OWD); print('OW only', summary(R)); MATS_OW = mats_present(R,F)
ADD = dict(KO)
ADD['end stone + chorus + shulker (no veins)'] = {'minecraft:end_stone','minecraft:chorus_fruit','minecraft:shulker_shell'}
ADD['all nether veins (no fortress items)'] = set().union(*[v for k,v in KO.items() if k.startswith('vein nether')]) | {'minecraft:netherrack','minecraft:quartz','minecraft:glowstone_dust','minecraft:soul_sand','minecraft:gold_nugget'}
ADD['all end veins + end stone'] = set().union(*[v for k,v in KO.items() if k.startswith('vein end')]) | {'minecraft:end_stone'}
for name, items in ADD.items():
    dims = OWD | ({'minecraft:the_nether'} if 'nether' in name else set()) | ({'minecraft:the_end'} if 'end' in name.split()[0:2] or 'end ' in name else set())
    R, F, _ = closure_m(OW | items, FL, dims)
    new = sorted(mats_present(R, F) - MATS_OW)
    print(f'+ {name}: {summary(R)}\n    new materials: {", ".join(new)[:900]}')
