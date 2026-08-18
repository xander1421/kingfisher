#!/usr/bin/env python3
"""Extract a typed knowledge graph from git history — commits, files, people.

WHY. filtered_mrr/hits_at_10 train on FB15k-237: 272,115 triples, a 2013
benchmark everyone has overfit. Git history is a real, large, TYPED graph that
nobody has tuned against, and the Linux kernel's patch log is the extreme case
-- ~1.3M commits, Signed-off-by chains, Fixes: trailers, subsystem structure.

The edges are genuinely relational, which is what link prediction needs:

    author   --authored-->     commit
    commit   --touches-->      file
    file     --under-->        subsystem      (path prefix)
    commit   --signed_off_by-> person         (trailer)
    commit   --reviewed_by-->  person         (trailer)
    commit   --fixes-->        commit         (Fixes: trailer, a real edge
                                               between two graph nodes, not a
                                               literal -- the useful kind)

METADATA ONLY. No blobs, no checkout. On a clone this means
`--filter=blob:none --no-checkout`, which is ~1-2 GB for the kernel rather than
~5 GB. Disk on this machine hit 100% once today and broke a write mid-edit, so
that distinction is not academic.

    python3 git2kg.py <repo> [--max N] [--out triples.tsv]
"""
import argparse
import collections
import os
import re
import subprocess
import sys

SEP = "\x1e"
# Capture the EMAIL inside <>, not the display name before it. Switching the
# author field to %ae while leaving this on the name put ONE entity type into
# TWO key spaces: the same human appeared as person:<email> when they authored
# and person:<name> when they signed off, so every trailer edge pointed at a
# node no author edge ever touched. Entity count went UP by 9 instead of down,
# which is the only reason it was noticed -- the graph would have looked fine.
TRAILER = re.compile(r'^(Signed-off-by|Reviewed-By|Reviewed-by|Acked-by|Tested-by|Co-developed-by):\s*.*?<([^>]+)>',
                     re.M)
FIXES = re.compile(r'^\s*Fixes:\s*([0-9a-f]{7,40})', re.M | re.I)


def norm_person(s):
    """Identity keyed on EMAIL, not display name.

    MEASURED on 3000 commits of stable-diffusion-webui: 214 distinct names
    against 217 distinct emails, and keying on the name got both directions
    wrong at once --
      6 emails carried MULTIPLE names, so one person became several nodes
        (automatic / automatic1111, logan / loganbooker,
         chengsong zhang / continue-revolution)
      9 names carried MULTIPLE emails, which is either one person split or two
        people silently merged, and the name alone cannot tell you which.
    ~7% of identities wrong on a small repo. The author node is a HUB in this
    graph, so a wrong identity does not corrupt one triple, it corrupts every
    edge through that person -- and link prediction is scored on exactly those.
    At kernel scale (decades, address changes, thousands of contributors) it is
    worse, not better.

    Email is not perfect either: one human with two addresses stays two nodes.
    That is a residual, and it is the SAFE direction -- splitting one person is
    a missing edge, merging two people is a fabricated one.
    """
    e = s.strip().lower()
    # An identity that is not an address is not an identity. Found 5 of these
    # after the switch to %ae, including a node literally named `person:` --
    # an EMPTY capture minted as a graph node, which is the e3b0c442 class in
    # a different file: nothing errored, the triple count did not move, and the
    # graph gained a hub that every malformed record pointed at. The other four
    # were bare usernames with no @, so they would also silently collide with
    # each other. Return None and let the caller drop the edge; a missing edge
    # is recoverable, a fabricated hub is not.
    if not e or '@' not in e:
        return None
    return 'person:' + e


def subsystem(path, depth=2):
    parts = path.split('/')
    return 'subsys:' + '/'.join(parts[:depth]) if len(parts) > 1 else 'subsys:_root'


def extract(repo, max_commits):
    # \x02 terminates the body so the --name-only file list that follows is
    # unambiguous. Without it the parser guessed "a line containing /" and found
    # 306 touches across 3000 commits -- root-level files were dropped and body
    # prose containing a slash was counted as a path. A file list is delimited
    # data; parsing it by heuristic is how you get a graph that is quietly wrong.
    # TWO delimiters, and both are load-bearing. \x1d LEADS each record --
    # trailing it does not work, because --name-only prints the file list AFTER
    # the format string, so a trailing separator lands before the files rather
    # than after them. \x02 terminates the body so the file list is unambiguous.
    # Collapsing these into one marker gave `authored: 1`: the whole log parsed
    # as a single record, and the counter still looked like a plausible number.
    fmt = '\x1d' + SEP.join(['%H', '%ae', '%B']) + '\x02'
    cmd = ['git', '-C', repo, 'log', f'--pretty=format:{fmt}', '--name-only', '--no-merges']
    if max_commits:
        cmd.insert(4, f'-n{max_commits}')
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=1800).stdout

    triples, stats = [], collections.Counter()
    for rec in out.split('\x1d'):
        if SEP not in rec:
            continue
        sha, author, rest = rec.split(SEP, 2)
        sha = sha.strip()
        if not sha:
            continue
        body, _, filesblock = rest.partition('\x02')
        files = [l.strip() for l in filesblock.split('\n') if l.strip()]

        c = 'commit:' + sha[:12]
        who_a = norm_person(author)
        if who_a:
            triples.append((who_a, 'authored', c)); stats['authored'] += 1
        else:
            stats['dropped_bad_identity'] += 1
        for f in set(files):
            triples.append((c, 'touches', 'file:' + f)); stats['touches'] += 1
            triples.append((('file:' + f), 'under', subsystem(f))); stats['under'] += 1
        for role, who in TRAILER.findall(body):
            p = norm_person(who)
            if not p:
                stats['dropped_bad_identity'] += 1
                continue
            triples.append((c, role.lower().replace('-', '_'), p))
            stats[role.lower()] += 1
        for tgt in FIXES.findall(body):
            triples.append((c, 'fixes', 'commit:' + tgt[:12].lower())); stats['fixes'] += 1
    return triples, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('--max', type=int, default=0)
    ap.add_argument('--out', default='triples.tsv')
    a = ap.parse_args()

    if not os.path.isdir(os.path.join(a.repo, '.git')):
        sys.exit(f'not a git repo: {a.repo}')

    triples, stats = extract(a.repo, a.max)
    uniq = sorted(set(triples))
    ents = {e for h, _, t in uniq for e in (h, t)}
    rels = {r for _, r, _ in uniq}

    with open(a.out, 'w') as f:
        for h, r, t in uniq:
            f.write(f'{h}\t{r}\t{t}\n')

    print(f'repo        {a.repo}')
    print(f'triples     {len(uniq)} unique ({len(triples)} raw)')
    print(f'entities    {len(ents)}')
    print(f'relations   {len(rels)}  {sorted(rels)}')
    print(f'by relation {dict(stats)}')
    print(f'-> {a.out}')
    # A graph with one relation type is not a KG, it is an edge list. Link
    # prediction needs several, and `fixes` is the only commit->commit edge.
    if len(rels) < 3:
        print('WARNING: fewer than 3 relation types -- too thin for link prediction')
    return 0


if __name__ == '__main__':
    sys.exit(main())
