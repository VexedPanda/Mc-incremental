import json,re,sys
from collections import defaultdict
sys.argv=[sys.argv[0], sys.argv[1] if len(sys.argv)>1 else 'ladder']+sys.argv[2:]
exec(open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/econ/ana/cost.py').read().rsplit("\nif __name__",1)[0])
PRE={'ingots':1,'dusts':1,'plates':1,'double_plates':2,'dense_plates':9,'foils':.25,'rods':.5,'long_rods':1,'bolts':.125,'screws':.125,
 'rings':.25,'rounds':1/9,'nuggets':1/9,'fine_wires':.125,'single_wires':.5,'double_wires':1,'quadruple_wires':2,'octal_wires':4,'hex_wires':8,
 'gears':4,'small_gears':1,'rotors':4,'springs':1,'small_springs':.25,'frames':2,'storage_blocks':9,'gems':1,'small_dusts':.25,'tiny_dusts':1/9,
 'lenses':.75,'exquisite_gems':4,'flawless_gems':2,'bolt':.125}
SUF={'ingot':1,'dust':1,'plate':1,'double_plate':2,'dense_plate':9,'foil':.25,'rod':.5,'long_rod':1,'bolt':.125,'screw':.125,'ring':.25,'round':1/9,
 'nugget':1/9,'fine_wire':.125,'single_wire':.5,'double_wire':1,'quadruple_wire':2,'gear':4,'small_gear':1,'rotor':4,'spring':1,'small_spring':.25,
 'frame':2,'block':9,'gem':1,'small_dust':.25,'tiny_dust':1/9,'lens':.75,'boule':0}
CAB={'single_cable':(.5,1),'double_cable':(1,1),'quadruple_cable':(2,2),'octal_cable':(4,3),'hex_cable':(8,5)}
recipes=defaultdict(list)
for l in open(D+'recipes.txt'):
    rid,js=l.split(' ',1); j=json.loads(js)
    t=j.get('type','')
    ins=[];outs=[]
    if t.startswith('minecraft:crafting'):
        if 'pattern' in j:
            cnt=defaultdict(int)
            for row in j['pattern']:
                for ch in row:
                    if ch!=' ': cnt[ch]+=1
            for ch,n in cnt.items():
                ing=j['key'].get(ch)
                if isinstance(ing,list): ing=ing[0]
                if ing: ins.append((ing,n))
        else:
            for ing in j.get('ingredients',[]):
                if isinstance(ing,list): ing=ing[0]
                ins.append((ing,1))
        r=j['result']; outs.append((r.get('id') or r.get('item'),r.get('count',1)))
    else:
        for x in j.get('inputs',{}).get('gtceu:item',[]):
            if x.get('chance',10000)==0: continue
            c=x['content']; ins.append((c.get('ingredient',c),c.get('count',1)))
        for x in j.get('inputs',{}).get('gtceu:fluid',[]):
            c=x['content']; ins.append(({'fluid':c.get('ingredient',{})},c.get('amount',0)))
        for x in j.get('outputs',{}).get('gtceu:item',[]):
            if x.get('chance',10000)<10000: continue
            c=x['content']; ing=c.get('ingredient',c); outs.append((ing.get('item') or ing.get('id'),c.get('count',1)))
    for o,n in outs:
        if o: recipes[o].append((rid,ins,n))
TIERS={'ulv':['vacuum_tube','nand_chip'],'lv':['basic_electronic_circuit','basic_integrated_circuit','microchip_processor'],
 'mv':['good_electronic_circuit','good_integrated_circuit','micro_processor'],'hv':['advanced_integrated_circuit','micro_processor_assembly','nano_processor'],
 'ev':['micro_processor_computer','nano_processor_assembly','quantum_processor'],'iv':['micro_processor_mainframe','nano_processor_computer','quantum_processor_assembly','crystal_processor'],
 'luv':['nano_processor_mainframe','quantum_processor_computer','crystal_processor_assembly','wetware_processor'],
 'zpm':['quantum_processor_mainframe','crystal_processor_computer','wetware_processor_assembly'],'uv':['crystal_processor_mainframe','wetware_processor_computer'],'uhv':['wetware_processor_mainframe']}
LEAF=defaultdict(float)
memo2={}
def item_val(i,depth=0):
    if i in memo2: return memo2[i]
    if depth>25: return 0
    memo2[i]=0
    v=None
    ns,n=i.split(':',1)
    if ns=='minecraft' and emc.get(i,0)>0: v=emc[i]
    if v is None and ns=='gtceu':
        for s in sorted(SUF,key=len,reverse=True):
            if n.endswith('_'+s):
                m=n[:-len(s)-1]
                if s=='boule': break
                if m in memo or m in comp or m in V or m in E_:
                    v=SUF[s]*mval(m); break
        if v is None:
            for s,(w,r) in CAB.items():
                if n.endswith('_'+s): v=w*mval(n[:-len(s)-1])+r*mval('rubber'); break
    if v is None and i in mat and i not in recipes: v=matcost(i)
    if v is None:
        best=None
        for rid,ins,cnt in recipes.get(i,[]):
            tot=sum(ing_val(x,depth+1)*k for x,k in ins)/max(cnt,1)
            if tot>0 and (best is None or tot<best): best=tot
        v=best
    EST={'gtceu:raw_crystal_chip':8192,'gtceu:quantum_eye':4096,'gtceu:quantum_star':150000,'minecraft:paper':32}
    if v is None and i in EST: v=EST[i]; LEAF['[E]'+i]+=1
    if v is None:
        v=emc.get(i,0); LEAF[i]+=1
    memo2[i]=v; return v
def ing_val(x,depth):
    if 'fluid' in x:
        f=x['fluid']; t=(f.get('tag') or f.get('fluid') or '').split(':')[-1].split('/')[-1]
        return mval(t)/144 if t not in GAS else 0
    if 'item' in x: return item_val(x['item'],depth)
    t=x.get('tag','')
    if t.startswith('gtceu:circuits/'): return circ(t.split('/')[-1])
    CT={'gtceu:resistors':['resistor','smd_resistor'],'gtceu:capacitors':['smd_capacitor'],'gtceu:transistors':['transistor','smd_transistor'],
        'gtceu:diodes':['diode','smd_diode'],'gtceu:inductors':['inductor','smd_inductor']}
    if t in CT: return min((item_val('gtceu:'+c,depth) or 1e18) for c in CT[t])
    EST={'gtceu:carbon_fibers':64,'gtceu:sticky_resin':16,'gtceu:petri_dish':256}
    if t in EST: LEAF['[E]'+t]+=1; return EST[t]
    if t.startswith('c:'):
        parts=t[2:].split('/')
        if len(parts)>=2 and parts[0] in PRE: return PRE[parts[0]]*mval(parts[-1])
        if parts[0]=='gems' and len(parts)>1: return mval(parts[-1])
        if parts[0]=='glass_blocks' or parts[0]=='glass': return 1
    LEAF[t]+=1; return 0
def circ(tier):
    return min(item_val('gtceu:'+c) or 1e18 for c in TIERS[tier])
if __name__=='__main__':
    for tier,cs in TIERS.items():
        print(tier, {c:round(item_val('gtceu:'+c)) for c in cs})
    print('unresolved leaves', sorted(LEAF)[:60])
