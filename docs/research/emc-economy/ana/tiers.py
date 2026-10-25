import sys
scen=sys.argv[1]
sys.argv=[sys.argv[0],scen]
exec(open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/econ/ana/recipes.py').read().rsplit("\nif __name__",1)[0])
E_['plutonium_241']=0 if scen=='current' else 16384
memo.clear(); memo2.clear()
iv=lambda i: item_val('gtceu:'+i if ':' not in i else i)
def multi(parts): return sum(n*iv(p) for p,n in parts)
T=['ulv','lv','mv','hv','ev','iv','luv','zpm','uv','uhv']
print(f"## scenario {scen}")
print('tier | circuit(cheapest) | hull | hull metal-only | macerator | macerator metal-only (GT recycling) | 16 machines+hatches est')
for t in T:
    c=circ(t) if t in TIERS else 0
    h=iv(t+'_machine_hull'); hm=matcost('gtceu:'+t+'_machine_hull')
    m=iv(t+'_macerator') if t!='ulv' else 0; mm=matcost('gtceu:'+t+'_macerator') if t!='ulv' else 0
    print(f"{t} | {c:,.0f} | {h:,.0f} | {hm:,.0f} | {m:,.0f} | {mm:,.0f} | {16*m:,.0f}")
steam=multi([('lp_steam_macerator',1)]); print('steam: lp_steam_macerator', iv('lp_steam_macerator'), 'hp boiler', iv('hp_steam_solid_boiler'), 'bronze casing',iv('bronze_machine_casing'))
ebf=multi([('electric_blast_furnace',1),('cupronickel_coil_block',16),('heatproof_machine_casing',11),('lv_energy_input_hatch',2),('lv_input_bus',1),('lv_output_bus',1),('maintenance_hatch',1),('lv_muffler_hatch',1)])
al=multi([('assembly_line',1),('solid_machine_casing',13),('ulv_input_bus',5),('laminated_glass',10),('assembly_line_unit',5),('assembly_line_casing',5),('assembly_line_grating',5),('iv_energy_input_hatch',2),('lv_output_bus',1),('data_access_hatch',1),('maintenance_hatch',1)])
f1=multi([('luv_fusion_reactor',1),('fusion_casing',95),('superconducting_coil',4),('luv_energy_input_hatch',16),('luv_input_hatch',2),('luv_output_hatch',1)])
f2=multi([('zpm_fusion_reactor',1),('fusion_casing_mk2',95),('fusion_coil',4),('zpm_energy_input_hatch',16),('zpm_input_hatch',2),('zpm_output_hatch',1)])
f3=multi([('uv_fusion_reactor',1),('fusion_casing_mk3',95),('fusion_coil',4),('uv_energy_input_hatch',16),('uv_input_hatch',2),('uv_output_hatch',1)])
for n,v in [('EBF (LV, 16 cupronickel coils)',ebf),('Assembly Line (5 slices, IV)',al),('Fusion MK1 (LuV, 16 hatches)',f1),('Fusion MK2 (ZPM)',f2),('Fusion MK3 (UV)',f3)]:
    print(f"{n} | {v:,.0f}")
for p in ['luv_fusion_reactor','fusion_casing','superconducting_coil','luv_energy_input_hatch','assembly_line','uv_machine_hull','uhv_machine_hull','iv_field_generator','uhpic_chip']:
    print(' part',p, f"{iv(p):,.0f}")
print('leaves', sorted(k for k in LEAF if not k.startswith('[E]'))[:40])
