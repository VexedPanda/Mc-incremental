import json,sys
from collections import Counter,defaultdict
exec(open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/econ/ana/areas.py').read().split("rows=[]")[0])
VEINS={'stone':{'apatite':['apatite','tricalcium_phosphate','pyrochlore'],'cassiterite':['tin','cassiterite'],'coal':['coal'],
 'copper_tin':['chalcopyrite','zeolite','cassiterite','realgar'],'galena':['galena','silver','lead'],'garnet_tin':['cassiterite_sand','garnet_sand','asbestos','diatomite'],
 'garnet':['red_garnet','yellow_garnet','amethyst','opal'],'iron':['goethite','yellow_limonite','hematite','malachite'],'lubricant':['soapstone','talc','glauconite_sand','pentlandite'],
 'magnetite':['magnetite','vanadium_magnetite','gold'],'mineral_sand':['basaltic_mineral_sand','granitic_mineral_sand','fullers_earth','gypsum'],
 'nickel':['garnierite','nickel','cobaltite','pentlandite'],'salts':['rock_salt','salt','lepidolite','spodumene'],'oilsands':['oilsands']},
 'deep':{'copper':['chalcopyrite','iron','pyrite','copper'],'diamond':['graphite','diamond','coal'],'lapis':['lazurite','sodalite','lapis','calcite'],
 'manganese':['grossular','spessartine','pyrolusite','tantalite'],'mica':['kyanite','mica','bauxite','pollucite'],'olivine':['bentonite','magnesite','olivine','glauconite_sand'],
 'redstone':['redstone','ruby','cinnabar'],'sapphire':['almandine','pyrope','sapphire','green_sapphire']}}
W={'stone':{'apatite':40,'cassiterite':80,'coal':80,'copper_tin':50,'galena':40,'garnet_tin':80,'garnet':40,'iron':120,'lubricant':40,'magnetite':80,'mineral_sand':80,'nickel':40,'salts':50,'oilsands':40},
   'deep':{'copper':80,'diamond':40,'lapis':40,'manganese':20,'mica':20,'olivine':20,'redstone':60,'sapphire':60}}
def val(m,mode): 
    if m not in gt_val: return 0
    v,k=gt_val[m]; return v*k*(2 if mode=='gt' else 1)
pervein=defaultdict(list)
for name,c in areas:
    mats=Counter()
    for b,n in c.items():
        if b.endswith('_ore') and b.startswith('gtceu:'):
            ns,m=ore_mat(b); layer='deep' if (b.startswith('gtceu:deepslate_') or b.startswith('gtceu:tuff_')) else 'stone'
            mats[(layer,m)]+=n
    for layer in ['stone','deep']:
        sc={v:sum(mats[(layer,m)] for m in ms) for v,ms in VEINS[layer].items()}
        top=max(sc,key=sc.get)
        # all ore blocks of this layer attributed (includes neighbour spill)
        blocks=sum(n for (l,m),n in mats.items() if l==layer)
        e=sum(n*val(m,'basic') for (l,m),n in mats.items() if l==layer)
        pervein[(layer,top)].append((blocks,e,sc[top]))
print('layer vein weight% | n areas | dominant-vein blocks | all GT ore blocks in layer | EMC basic (layer) | EMC GT-macerated')
for layer in ['stone','deep']:
    tw=sum(W[layer].values())
    for v in W[layer]:
        xs=pervein.get((layer,v),[])
        if xs:
            b=sum(x[0] for x in xs)/len(xs); e=sum(x[1] for x in xs)/len(xs); d=sum(x[2] for x in xs)/len(xs)
            print(f"{layer} {v} {100*W[layer][v]/tw:.0f}% | {len(xs)} | {d:.0f} | {b:.0f} | {e:,.0f} | {2*e:,.0f}")
        else: print(f"{layer} {v} {100*W[layer][v]/tw:.0f}% | 0 | - | - | - | -")
