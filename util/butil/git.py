
import subprocess
import os
from pathlib import Path
import inspect
import json

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
    out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=cwd).communicate()
    out = out.strip().decode('ascii')
    err = err.strip().decode('ascii')
    return out, err

def get_git_info():
    fn = inspect.stack()[0].filename
    path = Path(fn)
    path = path.parent
    
    status, err = _minimal_ext_cmd(['git', 'status', '--porcelain=v2', '--branch'], path)
    
    lines = status.split('\n')
    
    out = {
        'status': lines,
    }
    if err:
        info_path = Path(__file__).parent / 'git_info.json'
        if info_path.exists():
            with open(info_path) as f:
                out = json.load(f)
        else:
            out['status_stderr'] = err.split('\n')
    
    return out
