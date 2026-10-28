"""Compatibility entry: use the complete local server, never a static/fixture preview."""
from pathlib import Path
import os,sys
root=Path(__file__).resolve().parents[1]
python=root/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
os.execv(str(python if python.exists() else Path(sys.executable)),[str(python if python.exists() else Path(sys.executable)),str(root/'scripts/run-v4.py'),*sys.argv[1:]])
