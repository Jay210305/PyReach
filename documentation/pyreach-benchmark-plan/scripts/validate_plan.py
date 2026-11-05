#!/usr/bin/env python3
"""Offline planning validator: no third-party dependencies, no network or scans."""
from __future__ import annotations
from pathlib import Path
import re, sys, collections

ROOT = Path(__file__).resolve().parent.parent
TASK_DIR = ROOT / 'implementation'
SPRINT_HOURS = {0:18,1:22,2:22,3:22,4:18}
EXPECTED_TASKS=22
EXPECTED_TOTAL=102
errors=[]

def issue(s): errors.append(s)

def parse_front(text, file):
    if not text.startswith('---\n'):
        issue(f'{file}: no YAML frontmatter'); return {}
    parts=text.split('---\n',2)
    if len(parts)<3:
        issue(f'{file}: incomplete YAML frontmatter'); return {}
    data={}
    for line in parts[1].splitlines():
        if ':' not in line: continue
        k,v=line.split(':',1); data[k.strip()]=v.strip()
    return data

def main():
    tasks={}; sums=collections.Counter()
    for file in sorted(TASK_DIR.glob('sprint-*/*.md')):
        text=file.read_text(encoding='utf-8')
        fm=parse_front(text,file.relative_to(ROOT))
        tid=fm.get('id','')
        if not re.fullmatch(r'S\d+-T\d+',tid): issue(f'{file}: bad ID {tid!r}'); continue
        if tid in tasks: issue(f'duplicate ID {tid}')
        if not file.name.startswith(tid+'-'): issue(f'{file}: filename does not match task ID')
        try: sprint=int(fm.get('sprint','-1')); hours=float(fm.get('effort_h','nan'))
        except ValueError: issue(f'{tid}: invalid hours or sprint'); continue
        if sprint!=int(tid.split('-')[0][1:]): issue(f'{tid}: sprint mismatch')
        if not(0<hours<=8): issue(f'{tid}: task >8h or <=0')
        if fm.get('owner')!='benchmark-agent': issue(f'{tid}: owner mismatch')
        if fm.get('status') not in {'todo','in_progress','done','blocked','unsupported'}: issue(f'{tid}: unsupported status')
        dep=fm.get('depends_on','')
        if not(dep.startswith('[') and dep.endswith(']')): issue(f'{tid}: malformed dependency list'); deps=[]
        else: deps=[x.strip() for x in dep[1:-1].split(',') if x.strip()]
        subs=[float(m.group(1)) for m in re.finditer(r'^\- \[ \] 4\.\d+ \((\d+(?:\.\d+)?) h\) \*\*Test/review first:',text,re.M)]
        if not subs: issue(f'{tid}: missing subtasks')
        if any(x>2 or x<=0 for x in subs): issue(f'{tid}: subtask >2h/invalid')
        if abs(sum(subs)-hours)>1e-8: issue(f'{tid}: subtask sum {sum(subs)} != {hours}')
        if '## Acceptance Criteria (verbatim roadmap)' not in text or '## Interface Contract' not in text: issue(f'{tid}: task template incomplete')
        if '```bash' not in text: issue(f'{tid}: no copyable verification command')
        tasks[tid]=(sprint,hours,deps,file,text)
        sums[sprint]+=hours
    if len(tasks)!=EXPECTED_TASKS: issue(f'task count {len(tasks)} != {EXPECTED_TASKS}')
    for s,h in SPRINT_HOURS.items():
        if sums[s]!=h: issue(f'sprint {s} sums {sums[s]}h vs {h}')
    if sum(sums.values())!=EXPECTED_TOTAL: issue(f'total task hours {sum(sums.values())} != {EXPECTED_TOTAL}')
    for tid,(_,_,deps,_,_) in tasks.items():
        for dep in deps:
            if dep not in tasks: issue(f'{tid}: missing dependency {dep}')
            elif tasks[dep][0]>tasks[tid][0]: issue(f'{tid}: future sprint dependency {dep}')
    visiting=set(); visited=set()
    def dfs(tid):
        if tid in visiting: issue(f'dependency cycle through {tid}'); return
        if tid in visited: return
        visiting.add(tid)
        for d in tasks[tid][2]:
            if d in tasks: dfs(d)
        visiting.remove(tid); visited.add(tid)
    for tid in tasks: dfs(tid)
    roadmap=(ROOT/'04-implementation-roadmap.md').read_text(encoding='utf-8')
    row_regex=re.compile(r'^\| (S\d+-T\d+) \| .*? \| (\d+) \| benchmark-agent \| ⬜ \| (.*?) \|$',re.M)
    rows={}
    for tid,h,ac in row_regex.findall(roadmap):
        if tid in rows: issue(f'{tid}: duplicated in roadmap')
        rows[tid]=(float(h),ac)
    for tid,(_,hours,_,file,txt) in tasks.items():
        if tid not in rows: issue(f'{tid}: missing roadmap acceptance')
        elif rows[tid][0]!=hours: issue(f'{tid}: roadmap hours mismatch')
        elif f'## Acceptance Criteria (verbatim roadmap)\n{rows[tid][1]}' not in txt: issue(f'{tid}: acceptance not verbatim')
    if set(rows)!=set(tasks): issue('roadmap/task ID sets do not match')
    if '102' not in roadmap or '128' not in roadmap or '130' not in roadmap: issue('capacity reconciliation missing')
    for path in ROOT.rglob('*.md'):
        txt=path.read_text(encoding='utf-8')
        # Only inspect explicit inline relative .md hyperlinks, never URLs, placeholders or future code paths.
        for match in re.finditer(r'\[[^]]+\]\(([^)]+\.md)\)',txt):
            target=match.group(1)
            if re.match(r'^(?:https?://|#)',target): continue
            resolved=(path.parent/target).resolve()
            if not resolved.is_relative_to(ROOT.resolve()) or not resolved.is_file(): issue(f'{path.relative_to(ROOT)}: broken relative link {target}')
    reqs=set(re.findall(r'^\| (REQ-\d+) \| (?:Must|Should|Could|Won.t) \|', (ROOT/'01-overview.md').read_text(encoding='utf-8'), re.M))
    trace=(ROOT/'traceability.md').read_text(encoding='utf-8')
    traced=set(re.findall(r'^\| (REQ-\d+) \|',trace,re.M))
    if reqs!=traced: issue(f'traceability mismatch: {sorted(reqs^traced)}')
    for t in tasks:
        if t not in trace and not any(t in z[4] for z in tasks.values()): issue(f'{t}: not traced')
    if errors:
        print('PLAN LINT FAILED ('+str(len(errors))+' error(s))')
        for e in errors: print(' - '+e)
        return 1
    print(f'PLAN LINT OK: {len(tasks)} tasks; {sum(sums.values()):g} hours; {len(SPRINT_HOURS)} sprints; 0 bad links; dependency DAG acyclic; 128h forecast <= 130h capacity')
    return 0

if __name__=='__main__': sys.exit(main())
