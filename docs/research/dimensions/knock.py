exec(open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/dimana/tiers.py').read())
NE2 = NE | {'minecraft:nether_star'}
BASE = OW | NE2 | EN
DIMS = {'minecraft:overworld', 'minecraft:the_nether', 'minecraft:the_end'}
R0, F0, _ = closure_m(BASE, FL, DIMS)
targets = [f'gtceu:{t}_{c}' for t in TT for c in COMP] + MULTI
def lost(R):
    l = [x for x in targets if x in R0 and x not in R]
    by = defaultdict(list)
    for x in l:
        m = re.match(r'gtceu:(lv|mv|hv|ev|iv|luv|zpm|uv)_(.*)', x)
        if m and m.group(2) in COMP: by[m.group(1)].append(m.group(2))
        else: by['multi'].append(x.split(':')[1])
    first = next((t for t in TT if by.get(t)), None)
    return first, dict(by)
def vein_items(name):
    for l in open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/dimgt/veins.txt'):
        p = l.split()
        if len(p) > 2 and p[2] == name:
            pre = {'the_nether': 'netherrack_', 'the_end': 'endstone_'}[p[0]]
            return {f'gtceu:{pre}{m}_ore' for m in re.findall(r'(?:targets|block):([a-z0-9_]+)', l)}
    return set()
KO = {
 'nether quartz': {'minecraft:quartz', 'minecraft:nether_quartz_ore', 'gtceu:netherrack_nether_quartz_ore', 'minecraft:quartz_block'},
 'glowstone': {'minecraft:glowstone_dust', 'minecraft:glowstone'},
 'blaze rod': {'minecraft:blaze_rod'},
 'ender pearl': {'minecraft:ender_pearl'},
 'nether star (wither)': {'minecraft:nether_star'},
 'ghast tear': {'minecraft:ghast_tear'},
 'magma cream': {'minecraft:magma_cream'},
 'nether wart': {'minecraft:nether_wart'},
 'soul sand/soil': {'minecraft:soul_sand', 'minecraft:soul_soil'},
 'netherite/debris': {'minecraft:netherite_scrap', 'minecraft:ancient_debris'},
 'netherrack': {'minecraft:netherrack'},
 'end stone': {'minecraft:end_stone'},
 'chorus': {'minecraft:chorus_fruit', 'minecraft:chorus_flower', 'minecraft:chorus_plant'},
 'shulker shell': {'minecraft:shulker_shell'},
 'dragon egg': {'minecraft:dragon_egg'},
 'dragon breath': {'minecraft:dragon_breath'},
}
for l in open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/dimgt/veins.txt'):
    p = l.split()
    if p and p[0] in ('the_nether', 'the_end'): KO[f'vein {p[0][4:]}:{p[2]}'] = vein_items(p[2])
for name, items in KO.items():
    R, F, _ = closure_m(BASE - items, FL, DIMS)
    first, by = lost(R)
    print(f'KO {name}: first tier hit {first}; lost {by}')
