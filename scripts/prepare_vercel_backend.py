"""Create a self-contained inference deployment without CUDA/training packages."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import json

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
TARGET=ROOT/'.deploy'/'backend'

def prepare():
    target_backend=TARGET/'backend'
    target_backend.mkdir(parents=True,exist_ok=True)
    ignore=shutil.ignore_patterns('__pycache__','*.pyc')
    for name in ['app','agents']:
        shutil.copytree(ROOT/'backend'/name,target_backend/name,dirs_exist_ok=True,ignore=ignore)
    for path in ['__init__.py','ml/__init__.py','ml/recommendation.py']:
        dest=target_backend/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'backend'/path,dest)
    for name in ['data','artifacts/models','artifacts/graph','artifacts/metrics','artifacts/eda']:
        shutil.copytree(ROOT/'backend'/name,target_backend/name,dirs_exist_ok=True)
    (target_backend/'artifacts/reports').mkdir(parents=True,exist_ok=True)
    import joblib
    recommender=joblib.load(ROOT/'backend/artifacts/models/recommendation_model.pkl')
    recommender.export_serving(target_backend/'artifacts/models')
    # DataFrame pickles can carry optional Arrow dependencies from the training
    # machine. The serving model uses numeric arrays plus an explicit JSON schema.
    (target_backend/'artifacts/models/recommendation_model.pkl').unlink(missing_ok=True)
    # Seed only synthetic operational records, never local agent questions/reports.
    database=target_backend/'cirp.db'
    if database.exists(): database.unlink()
    env=os.environ.copy();env['DATABASE_URL']='sqlite:///'+str(database)
    subprocess.run([sys.executable,'-c','from backend.app.database import initialize; initialize()'],cwd=ROOT,env=env,check=True)
    shutil.copy2(ROOT/'backend/requirements-serving.txt',TARGET/'requirements.txt')
    (TARGET/'app.py').write_text('from backend.app.main import app\n',encoding='utf-8')
    (TARGET/'.python-version').write_text('3.12\n')
    # requirements.txt is the single runtime dependency manifest.
    if (TARGET/'pyproject.toml').exists(): (TARGET/'pyproject.toml').unlink()
    (TARGET/'vercel.json').write_text(json.dumps({'$schema':'https://openapi.vercel.sh/vercel.json','framework':'fastapi','functions':{'app.py':{'maxDuration':60}}},indent=2))
    (TARGET/'.vercelignore').write_text('__pycache__\n**/__pycache__\n*.pyc\n.vercel\n.env*\n.git\n*.log\n')
    size=sum(p.stat().st_size for p in TARGET.rglob('*') if p.is_file())
    print(f'Prepared {TARGET}\nSource and trained artifacts: {size/1024**2:.1f} MiB; no torch/scipy/sklearn serving dependencies.')

if __name__=='__main__':prepare()
