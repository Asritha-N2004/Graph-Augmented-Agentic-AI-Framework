import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
ARTIFACTS = ROOT / 'artifacts'
if os.getenv('VERCEL')=='1':
    # The deployment bundle is read-only. Each instance gets an isolated writable
    # research snapshot; use DATABASE_URL for a durable external database.
    runtime_root=Path(tempfile.mkdtemp(prefix='cirp-'))
    shutil.copytree(ARTIFACTS,runtime_root/'artifacts')
    ARTIFACTS=runtime_root/'artifacts'
    shutil.copy2(ROOT/'cirp.db',runtime_root/'cirp.db')
    default_database=runtime_root/'cirp.db'
else:
    default_database=ROOT/'cirp.db'
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{default_database}')
SEED = 42
for directory in [DATA, *[ARTIFACTS / x for x in ['models', 'graph', 'eda', 'reports', 'metrics']]]:
    directory.mkdir(parents=True, exist_ok=True)
