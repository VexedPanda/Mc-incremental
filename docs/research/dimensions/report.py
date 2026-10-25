import json, sys, re
from collections import defaultdict, Counter
exec(open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/dimana/closure.py').read())

def blocks_from_areas(paths, tag):
    s = Counter()
    for p in paths:
        try: f = open(p, encoding='utf-8', errors='replace')
        except FileNotFoundError: continue
        for line in f:
            i = line.find(tag)
            if i < 0: continue
            rest = line[i + len(tag):]
            j = rest.find('C={') if 'C={' in rest else rest.find(' {')
            if j < 0: continue
            js = rest[j + 2:].strip() if rest[j] == 'C' else rest[j + 1:].strip()
            try: d = json.loads(js)
            except Exception: continue
            for k, v in d.items(): s[k] += v
    return s

ow_blocks = blocks_from_areas([D1, D2], '[ECON] AREA ')
nether_blocks = blocks_from_areas([LOG2], '[DIMS] NETHER ')
end_blocks = blocks_from_areas([LOG2], '[DIMS] END ')

def items_of(blocks):
    out = set()
    for b in blocks:
        it = b2i.get(b)
        if it and it != 'minecraft:air': out.add(it)
    return out

# Common block drops without silk touch, mined by hand / any pickaxe
DROPS_OW = ['minecraft:cobblestone', 'minecraft:cobbled_deepslate', 'minecraft:raw_iron', 'minecraft:raw_copper', 'minecraft:raw_gold',
            'minecraft:coal', 'minecraft:diamond', 'minecraft:emerald', 'minecraft:lapis_lazuli', 'minecraft:redstone', 'minecraft:flint',
            'minecraft:clay_ball', 'minecraft:amethyst_shard', 'minecraft:stick', 'minecraft:wheat_seeds', 'minecraft:apple']
MOBS_OW = ['minecraft:rotten_flesh', 'minecraft:iron_ingot', 'minecraft:carrot', 'minecraft:potato', 'minecraft:bone', 'minecraft:arrow',
           'minecraft:gunpowder', 'minecraft:string', 'minecraft:spider_eye', 'minecraft:ender_pearl', 'minecraft:glowstone_dust',
           'minecraft:redstone', 'minecraft:sugar', 'minecraft:glass_bottle', 'minecraft:slime_ball', 'minecraft:copper_ingot',
           'minecraft:feather', 'minecraft:chicken', 'minecraft:beef', 'minecraft:leather', 'minecraft:porkchop', 'minecraft:mutton',
           'minecraft:white_wool', 'minecraft:egg', 'minecraft:ink_sac', 'minecraft:glow_ink_sac', 'minecraft:rabbit_hide',
           'minecraft:rabbit_foot', 'minecraft:phantom_membrane', 'minecraft:cod', 'minecraft:salmon', 'minecraft:nautilus_shell',
           'minecraft:milk_bucket', 'minecraft:honeycomb', 'minecraft:breeze_rod']
NETHER_EXTRA = ['minecraft:quartz', 'minecraft:gold_nugget', 'minecraft:glowstone_dust', 'minecraft:nether_wart', 'minecraft:netherite_scrap',
                'minecraft:ghast_tear', 'minecraft:magma_cream', 'minecraft:blaze_rod', 'minecraft:wither_skeleton_skull', 'minecraft:coal',
                'minecraft:bone', 'minecraft:gold_ingot', 'minecraft:obsidian', 'minecraft:crying_obsidian', 'minecraft:soul_sand',
                'minecraft:string', 'minecraft:leather', 'minecraft:porkchop', 'minecraft:ender_pearl', 'minecraft:fire_charge',
                'minecraft:nether_brick', 'minecraft:blackstone', 'minecraft:gravel']
END_EXTRA = ['minecraft:end_stone', 'minecraft:chorus_fruit', 'minecraft:chorus_flower', 'minecraft:shulker_shell', 'minecraft:ender_pearl',
             'minecraft:purpur_block', 'minecraft:elytra', 'minecraft:dragon_egg', 'minecraft:dragon_breath', 'minecraft:obsidian']

def gt_ore_items(dim):
    """Ore block items of every GT vein in that dimension, in its own stone type (from the vein jsons)."""
    pre = {'overworld': ['', 'deepslate_'], 'the_nether': ['netherrack_'], 'the_end': ['endstone_']}[dim]
    out = set()
    for l in open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/dimgt/veins.txt'):
        p = l.split()
        if not p or p[0] != dim: continue
        for tok in re.findall(r'(?:targets|block):([a-z0-9_]+)', l):
            for pr in pre:
                out.add(f'gtceu:{pr}{tok}_ore')
    return out

TRADER = ['minecraft:' + x for x in 'sea_pickle slime_ball glowstone nautilus_shell fern sugar_cane pumpkin kelp cactus dandelion poppy blue_orchid allium azure_bluet red_tulip orange_tulip white_tulip pink_tulip oxeye_daisy cornflower lily_of_the_valley wheat_seeds beetroot_seeds pumpkin_seeds melon_seeds acacia_sapling birch_sapling dark_oak_sapling jungle_sapling oak_sapling spruce_sapling cherry_sapling mangrove_propagule red_dye white_dye blue_dye pink_dye black_dye green_dye light_gray_dye magenta_dye yellow_dye gray_dye purple_dye light_blue_dye lime_dye orange_dye brown_dye cyan_dye brain_coral_block bubble_coral_block fire_coral_block horn_coral_block tube_coral_block vine brown_mushroom red_mushroom lily_pad small_dripleaf sand red_sand pointed_dripstone rooted_dirt moss_block tropical_fish_bucket pufferfish_bucket packed_ice blue_ice gunpowder podzol'.split()]
OW = set(TRADER) | items_of(ow_blocks) | set(DROPS_OW) | set(MOBS_OW) | gt_ore_items('overworld')
NE = items_of(nether_blocks) | set(NETHER_EXTRA) | gt_ore_items('the_nether')
EN = items_of(end_blocks) | set(END_EXTRA) | gt_ore_items('the_end')
FL = {'minecraft:water', 'minecraft:lava', 'minecraft:milk', 'gtceu:steam'}

scen = {}
scen['OW'] = closure(OW, FL, {'minecraft:overworld'})
scen['OW+N'] = closure(OW | NE, FL, {'minecraft:overworld', 'minecraft:the_nether'})
scen['OW+E'] = closure(OW | EN, FL, {'minecraft:overworld', 'minecraft:the_end'})
scen['ALL'] = closure(OW | NE | EN, FL, {'minecraft:overworld', 'minecraft:the_nether', 'minecraft:the_end'})
