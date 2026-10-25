exec(open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/dimana/add.py').read().split("R,F,_ = closure_m(OW, FL, OWD)")[0])
NV = set().union(*[v for k,v in KO.items() if k.startswith('vein nether')])
EV_ = set().union(*[v for k,v in KO.items() if k.startswith('vein end')])
NBASE = {'minecraft:netherrack','minecraft:quartz','minecraft:glowstone_dust','minecraft:soul_sand','minecraft:gold_nugget','minecraft:magma_cream','minecraft:ghast_tear','minecraft:nether_quartz_ore','minecraft:ancient_debris','minecraft:netherite_scrap'}
FORT = {'minecraft:blaze_rod','minecraft:wither_skeleton_skull','minecraft:nether_wart','minecraft:nether_star'}
N, E, O = 'minecraft:the_nether', 'minecraft:the_end', 'minecraft:overworld'
SCN = [
 ('A  OW (mined + mobs + trader)', OW, {O}),
 ('B  A + Nether, no fortress', OW|NV|NBASE, {O,N}),
 ('B2 A + Nether w/o molybdenum vein, no fortress', OW|(NV-KO['vein nether:molybdenum'])|NBASE, {O,N}),
 ('C  B + fortress (blaze, wither -> nether star)', OW|NV|NBASE|FORT, {O,N}),
 ('D  A + End stone only (no veins)', OW|{'minecraft:end_stone','minecraft:chorus_fruit','minecraft:shulker_shell'}, {O,E}),
 ('E  A + End stone + all End veins', OW|EV_|{'minecraft:end_stone','minecraft:chorus_fruit'}, {O,E}),
 ('F  B + E (Nether no fortress + End)', OW|NV|NBASE|EV_|{'minecraft:end_stone','minecraft:chorus_fruit'}, {O,N,E}),
 ('G  C + E (everything)', OW|NV|NBASE|FORT|EV_|{'minecraft:end_stone','minecraft:chorus_fruit','minecraft:shulker_shell'}, {O,N,E}),
 ('H  G minus naquadah vein', OW|NV|NBASE|FORT|(EV_-KO['vein end:naquadah'])|{'minecraft:end_stone'}, {O,N,E}),
 ('I  A + nether star only (as if Wither were given)', OW|{'minecraft:nether_star'}, {O}),
 ('J  A + end stone + nether star + sulfur vein + molybdenum', OW|{'minecraft:end_stone','minecraft:nether_star'}|KO['vein nether:sulfur']|KO['vein nether:molybdenum'], {O,N,E}),
]
for name, seeds, dims in SCN:
    R, F, via = closure_m(seeds, FL, dims)
    miss = {t: [c for c in COMP if f'gtceu:{t}_{c}' not in R] for t in TT}
    print(f'== {name}: highest complete tier {highest_full(R)}; multis {[m.split(":")[1].replace("_coil_block","C").replace("_fusion_reactor","F") for m in MULTI if m in R]}')
    for t in TT:
        if miss[t] and len(miss[t]) < len(COMP): print(f'     {t} missing {miss[t]}')
        elif miss[t]: print(f'     {t} none'); break
