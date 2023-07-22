
import subprocess
import os
from pathlib import Path
import inspect

def _minimal_ext_cmd(cmd, cwd):
    # construct minimal environment
    env = {}
    for k in ['SYSTEMROOT', 'PATH']:
        v = os.environ.get(k)
        if v is not None:
            env[k] = v
    # LANGUAGE is used on win32
    env['LANGUAGE'] = 'C'
    env['LANG'] = 'C'
    env['LC_ALL'] = 'C'
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env, cwd=cwd).communicate()[0]
    out = out.strip().decode('ascii')
    return out

def get_git_info():
    fn = inspect.stack()[0].filename
    path = Path(fn)
    path = path.parent
    
    status = _minimal_ext_cmd(['git', 'status', '--porcelain=v2', '--branch'], path)
    
    lines = status.split('\n')
    
    return {
        'status': lines,
    }
