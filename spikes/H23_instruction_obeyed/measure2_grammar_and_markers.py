import re, sys, os
sys.path.insert(0,'spikes/harness')
import refcheck
files=[f for f in refcheck.harness_files() if f.endswith(('.sh','.py','.hook'))]
TOP=set(os.listdir('.'))
EMIT = re.compile(r'(?:^|\s|\|)(?:echo|printf|print|sys\.stderr\.write|sys\.stdout\.write|cat\s*<<)')
# GRAMMAR, not keyword guessing: "<interpreter> <repo-path>" inside an emitted
# string is an instruction to RUN something.
RUNCMD = re.compile(r'\b(?:sh|bash|python3|python)\s+((?:\./)?[\w.\-]+(?:/[\w.\-]+)+)')
# A marker the reader is told to produce.
MARKER = re.compile(r'\b([A-Z][A-Z0-9]{2,}(?:[-_][A-Z0-9]+)+)\b')
def emitted_lines(path):
    out=[]; inh=None
    for n,l in enumerate(open(path,encoding='utf-8',errors='replace').read().splitlines(),1):
        st=l.strip()
        if inh:
            if st==inh: inh=None; continue
            out.append((n,l)); continue
        m=re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", l)
        if m and EMIT.search(l): inh=m.group(1)
        if st.startswith('#'): continue
        if EMIT.search(l): out.append((n,l))
    return out
runs=[]; marks=[]
for f in files:
    try: el=emitted_lines(f)
    except OSError: continue
    eset={n for n,_ in el}
    allines=open(f,encoding='utf-8',errors='replace').read().splitlines()
    for n,l in el:
        for m in RUNCMD.finditer(l):
            p=m.group(1).rstrip('.,;:)"\'')
            b=p[2:] if p.startswith('./') else p
            if any(c in p for c in '$*?<>'): continue
            if b.split('/')[0] not in TOP and not p.startswith('./'): continue
            runs.append((f,n,p,os.path.exists(b)))
        for m in MARKER.finditer(l):
            tok=m.group(1)
            # does it appear in a NON-emitted line of the same file?
            elsewhere=any(tok in ln for i,ln in enumerate(allines,1)
                          if i not in eset and not ln.strip().startswith('#'))
            marks.append((f,n,tok,elsewhere))
print(f"A) emitted '<interpreter> <repo path>' instructions: {len(runs)}")
badr=[r for r in runs if not r[3]]
print(f"   naming a path that does NOT exist: {len(badr)}")
for r in badr: print("     MISSING", f"{r[0]}:{r[1]}", r[2])
print(f"\nB) markers named in emitted strings: {len(marks)}")
badm=[m for m in marks if not m[3]]
print(f"   NOT present in any non-message line of the same file: {len(badm)}")
seen=set()
for m in badm:
    k=(m[0],m[2])
    if k in seen: continue
    seen.add(k); print("     ORPHAN", f"{m[0]}:{m[1]}", m[2])
