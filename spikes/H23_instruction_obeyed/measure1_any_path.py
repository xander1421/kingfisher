import re, sys, os
sys.path.insert(0,'spikes/harness')
import refcheck
files=[f for f in refcheck.harness_files() if f.endswith(('.sh','.py','.hook'))]
TOP=set(os.listdir('.'))
EMIT = re.compile(r'(?:^|\s|\|)(?:echo|printf|print|sys\.stderr\.write|sys\.stdout\.write|cat\s*<<)')
PATH = re.compile(r'(?<![\w/.-])((?:\./)?[\w.\-]+(?:/[\w.\-]+)+)')
rows=[]
for f in files:
    try: lines=open(f,encoding='utf-8',errors='replace').read().splitlines()
    except OSError: continue
    inheredoc=None
    for n,l in enumerate(lines,1):
        s=l.rstrip()
        st=s.strip()
        if inheredoc:
            if st==inheredoc: inheredoc=None; continue
            emitted=True
        else:
            m=re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", s)
            if m and EMIT.search(s): inheredoc=m.group(1)
            if st.startswith('#'): continue
            emitted=bool(EMIT.search(s))
        if not emitted: continue
        for pm in PATH.finditer(s):
            cand=pm.group(1).rstrip('.,;:)"\'')
            body=cand[2:] if cand.startswith('./') else cand
            if not body or body.split('/')[0] not in TOP: continue
            if any(c in cand for c in '$*?<>'): continue
            rows.append((f,n,cand,os.path.exists(body)))
print(f"repo paths inside EMITTED strings: {len(rows)}")
bad=[r for r in rows if not r[3]]
print(f"  naming a path that does NOT exist: {len(bad)}")
for r in bad: print("   MISSING", f"{r[0]}:{r[1]}", r[2])
from collections import Counter
print("\n  by file:", Counter(r[0] for r in rows).most_common(8))
