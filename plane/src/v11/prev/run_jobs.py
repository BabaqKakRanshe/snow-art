"""Runs the composite jobs (jobs.txt: prefix|variant|out|json) two at a time."""
import subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor
os.chdir('/home/claude/plane/v11/prev')
jobs = [l.strip().split('|') for l in open(sys.argv[1] if len(sys.argv) > 1 else 'jobs.txt') if l.strip()]


def run(j):
    r = subprocess.run(['python3', 'urp_emulate.py'] + j, capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ['?'])[-1]
    return '%s %s -> %s %s' % (j[0], j[1], last, r.stderr.strip()[-300:] if r.returncode else '')


with ThreadPoolExecutor(2) as ex:
    for line in ex.map(run, jobs):
        print(line, flush=True)
print('ALLDONE', flush=True)
