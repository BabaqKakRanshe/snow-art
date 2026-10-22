"""Compile the HLSLPROGRAM blocks of a Unity URP .shader with DXC against the real URP 17 (6000.0) ShaderLibrary.
python3 check.py <file.shader> [extra defines...]   -> compiles every pass, vertex + fragment, with and without fog keywords."""
import sys, re, subprocess, os, itertools
S = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad'
DXC = S + '/dxc/bin/dxc'
ROOT = S + '/gfx'
src = open(sys.argv[1]).read()
blocks = re.findall(r'HLSLPROGRAM(.*?)ENDHLSL', src, re.S)
ok = True
for bi, b in enumerate(blocks):
    vert = re.search(r'#pragma\s+vertex\s+(\w+)', b).group(1)
    frag = re.search(r'#pragma\s+fragment\s+(\w+)', b).group(1)
    variants = [[], ['FOG_EXP2'], ['FOG_LINEAR']]
    if '_LIGHT_COOKIES' in b: variants.append(['_LIGHT_COOKIES'])
    for var in variants:
        for stage, entry, prof in (('VERTEX', vert, 'vs_6_0'), ('FRAGMENT', frag, 'ps_6_0')):
            hdr = ['#define SHADER_API_D3D11 1', '#define SHADER_TARGET 45', '#define UNITY_VERSION 60000067',
                   '#define SHADER_STAGE_%s 1' % stage, '#define UNITY_COLORSPACE_LINEAR 1'] + ['#define %s 1' % d for d in var + sys.argv[2:]]
            body = re.sub(r'#pragma[^\n]*', '', b)
            fn = 'tmp_%d_%s_%s.hlsl' % (bi, stage, '_'.join(var) or 'nofog')
            open(fn, 'w').write('\n'.join(hdr) + '\n' + body)
            r = subprocess.run([DXC, '-T', prof, '-E', entry, '-HV', '2018', '-I', ROOT, '-Wno-conversion', '-Wno-ignored-attributes',
                                '-Wno-parentheses-equality', fn, '-Fo', fn + '.o'],
                               capture_output=True, text=True)
            errs = [l for l in r.stderr.splitlines() if 'error' in l]
            warns = [l for l in r.stderr.splitlines() if 'warning' in l and 'Packages/' not in l]
            status = 'OK' if r.returncode == 0 else 'FAIL'
            if r.returncode != 0: ok = False
            print('pass %d %-8s %-12s %s' % (bi, stage, '+'.join(var) or '-', status))
            for l in (errs[:12] if r.returncode else []) + warns[:6]: print('   ', l[:300])
print('ALL OK' if ok else 'ERRORS')
