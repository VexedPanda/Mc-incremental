import json,re,sys,statistics as st
from collections import Counter,defaultdict
D='/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/econ/'
emc=json.load(open(D+'emc.json'))
areas=[]
for f in sys.argv[1:]:
    for l in open(D+f):
        if l.startswith('[ECON] AREA '):
            p=l.split(' ',4); areas.append((f+':'+p[2],json.loads(p[4])))
N=len(areas)
STONES=['deepslate','tuff','granite','diorite','andesite','red_granite','marble','basalt','sand','red_sand','gravel','netherrack','endstone','blackstone']
def ore_mat(b):
    ns,n=b.split(':'); n=n[:-4]
    for s in sorted(STONES,key=len,reverse=True):
        if n.startswith(s+'_'): n=n[len(s)+1:]; break
    return ns,n
# per ore block EMC: (smelt/drop route, GT macerate route ~2x mult + 14% byproduct ignored)
IRON,CU,SN,PB,AG,NI,AU=256,128,256,512,512,1024,2048
gt_val={ # material: (output EMC per unit, ore multiplier)
 'goethite':(IRON,1),'hematite':(IRON,1),'yellow_limonite':(IRON,1),'magnetite':(IRON,1),'pyrite':(IRON,1),
 'basaltic_mineral_sand':(IRON,1),'granitic_mineral_sand':(IRON,1),'iron':(IRON,1),
 'chalcopyrite':(CU,1),'malachite':(CU,1),'copper':(CU,1),'tetrahedrite':(CU,1),
 'cassiterite':(SN,2),'cassiterite_sand':(SN,2),'tin':(SN,1),
 'galena':(PB,1),'lead':(PB,1),'silver':(AG,1),'garnierite':(NI,1),'pentlandite':(NI,1),'nickel':(NI,1),'gold':(AU,1),
 'coal':(128,2),'redstone':(64,5),'lapis':(864,6),'ruby':(2048,1),'sapphire':(2048,1),'diamond':(8192,1),'emerald':(16384,1),
 'amethyst':(32,1),
}
van_drop={'coal':128,'iron':IRON,'copper':3.5*CU,'gold':AU,'redstone':4.5*64,'lapis':6.5*864,'diamond':8192,'emerald':16384}
van_mac={'coal':2*128,'iron':2*IRON,'copper':7*CU,'gold':2*AU,'redstone':10*64,'lapis':6.5*864,'diamond':8192,'emerald':16384}  # GT macerator 2x on raw ores; gems/lapis/redstone kept at drop value except redstone silk+macerate
rows=[]
gt_zero=Counter(); gt_mat_tot=Counter(); van_tot=Counter()
for name,c in areas:
    r=defaultdict(float)
    for b,n in c.items():
        if b.endswith('_ore'):
            ns,m=ore_mat(b)
            if ns=='minecraft':
                r['van_basic']+=n*van_drop[m]; r['van_gt']+=n*van_mac[m]; van_tot[m]+=n
            else:
                gt_mat_tot[m]+=n
                if m in gt_val:
                    v,k=gt_val[m]; r['gt_basic']+=n*v*k; r['gt_gt']+=n*v*k*2
                else: gt_zero[m]+=n
                r['gt_blocks']+=n
        else:
            v=emc.get(b, emc.get(b.replace('minecraft:','minecraft:'),0))
            if v and v>0: r['bulk']+=n*v
            if 'log' in b or 'stem' in b: r['logs']+=n*32
    rows.append((name,r))
def s(k): 
    xs=[r[k] for _,r in rows]; xs.sort(); return st.mean(xs), xs[0], xs[len(xs)//2], xs[-1]
print('areas',N)
for k in ['bulk','logs','van_basic','van_gt','gt_blocks','gt_basic','gt_gt']:
    m,lo,med,hi=s(k); print(f"{k:10s} mean {m:12,.0f} min {lo:12,.0f} med {med:12,.0f} max {hi:12,.0f}")
tot_basic=[r['bulk']+r['van_basic']+r['gt_basic'] for _,r in rows]; tot_gt=[r['bulk']+r['van_gt']+r['gt_gt'] for _,r in rows]
for nm,xs in [('TOTAL basic',tot_basic),('TOTAL gt',tot_gt)]:
    xs=sorted(xs); print(nm, f"mean {st.mean(xs):,.0f} p10 {xs[len(xs)//10]:,.0f} med {xs[len(xs)//2]:,.0f} p90 {xs[9*len(xs)//10]:,.0f} max {xs[-1]:,.0f}")
print('vanilla ore blocks/area', {k:round(v/N,1) for k,v in van_tot.most_common()})
print('GT ore blocks/area by material', {k:round(v/N,1) for k,v in gt_mat_tot.most_common()})
print('GT unvalued blocks/area', round(sum(gt_zero.values())/N), 'of', round(sum(gt_mat_tot.values())/N))
# bulk breakdown
bulk=Counter()
for _,c in areas:
    for b,n in c.items():
        if not b.endswith('_ore'):
            v=emc.get(b,0)
            if v>0: bulk[b]+=n*v
print('bulk top', [(k,round(v/N)) for k,v in bulk.most_common(12)])
json.dump([(n,dict(r)) for n,r in rows],open(D+'ana/rows.json','w'))
