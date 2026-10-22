import marshal, sys, types, importlib.util
def load_pyc(p):
    with open(p,'rb') as f:
        f.read(16)
        return marshal.load(f)
def funcs(co, prefix=''):
    out = {}
    for c in co.co_consts:
        if isinstance(c, types.CodeType):
            name = prefix + c.co_name
            out[name] = c
            out.update(funcs(c, name + '.'))
    return out
def sig(c):
    consts = tuple(x for x in c.co_consts if not isinstance(x, types.CodeType))
    return (c.co_code, consts, c.co_names)
for mod in sys.argv[1:]:
    old = load_pyc(f'/home/claude/uaz/__pycache__/{mod}.cpython-311.pyc')
    src = open(f'/home/claude/uaz/{mod}.py').read()
    new = compile(src, f'/home/claude/uaz/{mod}.py', 'exec')
    fo, fn = funcs(old), funcs(new)
    if sig(old) != sig(new): print(mod, 'MODULE-LEVEL differs')
    for k in sorted(set(fo) | set(fn)):
        if k not in fo: print(mod, 'NEW func', k); continue
        if k not in fn: print(mod, 'REMOVED func', k); continue
        if sig(fo[k]) != sig(fn[k]):
            co, cn = fo[k], fn[k]
            ac = [x for x in co.co_consts if not isinstance(x, types.CodeType)]
            bc = [x for x in cn.co_consts if not isinstance(x, types.CodeType)]
            print(mod, 'CHANGED', k, 'line', cn.co_firstlineno)
            print('   old-only consts:', [x for x in ac if x not in bc][:20])
            print('   new-only consts:', [x for x in bc if x not in ac][:20])
