import re, sys, os
sys.path.insert(0,'spikes/harness')
import refcheck
files=[f for f in refcheck.harness_files() if f.endswith(('.sh','.py','.hook'))]
TOP=set(os.listdir('.'))
# A MESSAGE, not a write: `echo X > f` and `printf ... >> f` are file writes.
EMIT = re.compile(r'(?:^|\s|\|)(?:echo|printf|print|sys\.stderr\.write|sys\.stdout\.write|cat\s*<<)')
REDIR = re.compile(r'>[>&]?\s*\S')
# A PATH, not the next word: require a slash or a script extension. Without this
# the pattern matched `sh will`, `sh ---`, `python -c` out of prose.
RUNCMD = re.compile(r'\b(?:sh|bash|python3|python)\s+((?:\./)?[\w.\-]+/[\w.\-/]+|(?:\./)?[\w.\-]+\.(?:sh|py))')
def emitted(path):
    out=[]; inh=None
    for n,l in enumerate(open(path,encoding='utf-8',errors='replace').read().splitlines(),1):
        st=l.strip()
        if inh:
            if st==inh: inh=None; continue
            out.append((n,l)); continue
        m=re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", l)
        if m and EMIT.search(l): inh=m.group(1)
        if st.startswith('#'): continue
        if EMIT.search(l) and not REDIR.search(l): out.append((n,l))
    return out
tot=0; bad=[]
for f in files:
    try: src=open(f,encoding='utf-8',errors='replace').read()
    except OSError: continue
    scratch = 'mktemp -d' in src or 'mkdtemp' in src
    for n,l in emitted(f):
        for m in RUNCMD.finditer(l):
            p=m.group(1).rstrip('.,;:)"\'')
            if any(c in p for c in '$*?<>'): continue
            b=p[2:] if p.startswith('./') else p
            if '/' not in b:
                if scratch: continue          # bare ./x inside a suite with its own ROOT
            elif b.split('/')[0] not in TOP: continue
            tot+=1
            if not os.path.exists(b): bad.append((f,n,p))
print(f"instructions checked: {tot}   unresolved: {len(bad)}")
for r in bad: print("   MISSING", f"{r[0]}:{r[1]}", r[2])
