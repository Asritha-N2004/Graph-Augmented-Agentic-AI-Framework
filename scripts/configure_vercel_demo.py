"""Configure the authorized public synthetic demo; secrets travel over stdin only."""
import secrets
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/'.deploy/tooling/node_modules/vercel/dist/index.js'

def put(folder,name,value,secret=True):
    result=subprocess.run(['node',str(CLI),'env','add',name,'--environment','production','--sensitive' if secret else '--no-sensitive','--yes','--force','--cwd',str(ROOT/folder),'--no-color'],input=value,text=True,capture_output=True)
    if result.returncode:
        raise RuntimeError((result.stdout+result.stderr).replace(value,'[redacted]'))
    print(f'Configured {folder}: {name}',flush=True)

if __name__=='__main__':
    service=secrets.token_urlsafe(32)
    put('.deploy/backend','BACKEND_API_KEY',service)
    put('.deploy/backend','ENABLE_TRAINING_API','false',False)
    put('frontend','BACKEND_API_KEY',service)
    put('frontend','AUTH_SECRET',secrets.token_urlsafe(48))
    put('frontend','AUTH_EMAIL','analyst@cirp.local',False)
    put('frontend','AUTH_PASSWORD','CIRP-Demo-2026')
    put('frontend','PUBLIC_DEMO_LOGIN','true',False)
