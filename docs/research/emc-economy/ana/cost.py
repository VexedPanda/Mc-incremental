import json,re,sys
from collections import defaultdict
D='/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/econ/'
emc=json.load(open(D+'emc.json')); C=json.load(open(D+'ana/comp.json'))
snake=lambda s: re.sub(r'(?<!^)([A-Z])',r'_\1',s).lower()
comp={k:[(snake(a),b) for a,b in v if isinstance(b,int)] for k,v in C['comp'].items()}
SCEN=sys.argv[1] if len(sys.argv)>1 else 'ladder'
# [V] ProjectE / pack values per ingot-or-dust unit
V={'iron':256,'wrought_iron':256,'copper':128,'tin':256,'lead':512,'silver':512,'nickel':1024,'gold':2048,'aluminium':1024,'zinc':512,
   'steel':512,'bronze':160,'brass':224,'red_alloy':384,'platinum':4096,'osmium':512,'uranium_238':4096,'uranium':4096,
   'diamond':8192,'emerald':16384,'ruby':2048,'sapphire':2048,'redstone':64,'lapis':864,'coal':128,'glowstone':384,'nether_quartz':256,
   'ender_pearl':1024,'ender_eye':1792,'nether_star':139264,'amethyst':32,'clay':16,'flint':4,'glass':1,'stone':1,'obsidian':64,'brick':16,
   'quartzite':256,'blaze':768}
# [E] assumed ladder for materials ProjectE/pack leave at 0 (per unit), roughly 'rarity in GT worldgen x iron'
E_={'chromium':1024,'manganese':512,'cobalt':1024,'titanium':2048,'vanadium':2048,'molybdenum':2048,'tungsten':4096,'magnesium':256,
   'niobium':4096,'neodymium':2048,'samarium':4096,'gallium':1024,'indium':2048,'yttrium':2048,'barium':512,'palladium':4096,
   'rhodium':8192,'ruthenium':8192,'iridium':16384,'osmium_rare':16384,'europium':16384,'americium':32768,'naquadah':32768,
   'enriched_naquadah':65536,'naquadria':131072,'trinium':65536,'duranium':65536,'tritanium':131072,'darmstadtium':131072,
   'neutronium':524288,'beryllium':1024,'boron':256,'arsenic':256,'phosphorus':64,'mercury':256,'calcium':32,'silicon':128,
   'sulfur':32,'carbon':64,'lithium':512,'thorium':1024,'antimony':512,'bismuth':512,'cadmium':512,'potassium':32,'sodium':16,
   'strontium':512,'caesium':1024,'tantalum':4096,'plutonium_239':16384,'cerium':1024,'lanthanum':1024,'graphite':64,
   'rubber':64,'silicone_rubber':128,'styrene_butadiene_rubber':128,'polyethylene':64,'polyvinyl_chloride':64,'polytetrafluoroethylene':256,
   'polybenzimidazole':1024,'epoxy':128,'polyphenylene_sulfide':256,'borosilicate_glass':16,'wood':8,'treated_wood':8,'paper':32,
   'gallium_arsenide':512,'black_steel':400,'tin_alloy':256,'soldering_alloy':300,'annealed_copper':128,'electrotine':128,'blue_alloy':300,
   'graphene':128,'magnetite':256,'quartz':256,'certus_quartz':256,'ice':1,'water':0,'ender_pearl':1024}
GAS={'oxygen','hydrogen','nitrogen','chlorine','fluorine','argon','helium','neon','water'}
if SCEN=='current':  # only [V] values count; everything else 0
    E_={k:0 for k in E_}
memo={}
def mval(m):
    m=m.replace('magnetic_','') if m.startswith('magnetic_') else m
    if m in memo: return memo[m]
    memo[m]=0
    if SCEN=='ladder' and m=='osmium': v=E_['osmium_rare']
    elif m in V: v=V[m]
    elif m in E_: v=E_[m]
    elif m in GAS: v=0
    elif m in comp and comp[m]:
        tot=sum(n for _,n in comp[m]); v=sum(n*mval(a) for a,n in comp[m])/tot
    else:
        v=None
    if v is None:
        UNK.add(m); v=0
    memo[m]=v; return v
UNK=set()
mat={}
for l in open(D+'matinfo.txt'):
    i,rest=l.strip().split(' ',1) if ' ' in l.strip() else (l.strip(),'')
    mat[i]=[(p.split('=')[0],float(p.split('=')[1])) for p in rest.split(',') if '=' in p]
def matcost(i): return sum(a*mval(m) for m,a in mat.get(i,[]))
if __name__=='__main__':
    for i in sys.argv[2:]: print(i, round(matcost(i)), mat.get(i))
