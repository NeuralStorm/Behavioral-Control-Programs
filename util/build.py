
import json
from pathlib import Path
import butil.git as git

def _build():
    build_dir = Path(__file__).parent
    
    git_info = git.get_git_info()
    out_path = build_dir/'butil/git_info.json'
    
    if 'status_stderr' in git_info:
        out_path.unlink(missing_ok=True)
    else:
        with open(out_path, 'w') as f:
            json.dump(git_info, f)

def build(setup_kwargs):
    """
    Entrypoint for build script
    """
    _build()

if __name__ == "__main__":
    build({})
