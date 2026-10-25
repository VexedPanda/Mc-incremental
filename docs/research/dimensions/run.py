exec(open('/tmp/claude-0/-home-user-Mc-incremental/25f736d2-988d-5aaf-a828-5d280d2bb429/scratchpad/dimana/report.py').read())
SC = {'OW': (OW, {'minecraft:overworld'}), 'OW+N': (OW | NE, {'minecraft:overworld', 'minecraft:the_nether'}),
      'OW+E': (OW | EN, {'minecraft:overworld', 'minecraft:the_end'}),
      'ALL': (OW | NE | EN, {'minecraft:overworld', 'minecraft:the_nether', 'minecraft:the_end'})}
RES = {k: closure_m(s, FL, d) for k, (s, d) in SC.items()}
