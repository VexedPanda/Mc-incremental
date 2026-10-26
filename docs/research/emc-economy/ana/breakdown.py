import sys
from collections import Counter
sys.argv=[sys.argv[0],'ladder']
exec(open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/econ/ana/cost.py').read().rsplit("\nif __name__",1)[0])
E_['plutonium_241']=16384
NO_OW={'tungsten','naquadah','enriched_naquadah','naquadria','trinium','duranium','tritanium','europium','americium','uranium_238','uranium','plutonium_241','plutonium_239','neutronium','darmstadtium','nether_star'}
def leaves(m,amt,acc):
    m2=m.replace('magnetic_','')
    if m2 in V or m2 in E_ or m2 in GAS or m2 not in comp or m2=='osmium':
        acc[m2]+=amt*mval(m2); return
    tot=sum(n for _,n in comp[m2])
    for a,n in comp[m2]: leaves(a,amt*n/tot,acc)
kits={'LV':[('lv_macerator',16),('electric_blast_furnace',1),('cupronickel_coil_block',16),('heatproof_machine_casing',11)],
 'MV':[('mv_macerator',16)],'HV':[('hv_macerator',16),('cleanroom',1)],'EV':[('ev_macerator',16)],
 'IV':[('iv_macerator',16),('assembly_line',1),('assembly_line_unit',5),('assembly_line_casing',5),('iv_machine_hull',4)],
 'LuV':[('luv_macerator',16),('fusion_casing',95),('luv_machine_hull',16)],'ZPM':[('zpm_macerator',16),('fusion_casing_mk2',95)],
 'UV':[('uv_macerator',16),('fusion_casing_mk3',95)],'UHV':[('uhv_machine_hull',16)]}
for k,parts in kits.items():
    acc=Counter()
    for p,n in parts:
        for m,a in mat.get('gtceu:'+p,[]): leaves(m,a*n,acc)
    tot=sum(acc.values()) or 1
    no=sum(v for m,v in acc.items() if m in NO_OW)
    top=', '.join(f"{m} {100*v/tot:.0f}%" for m,v in acc.most_common(4))
    print(f"{k} | metal-only {tot:,.0f} | non-overworld share {100*no/tot:.0f}% | top: {top}")
