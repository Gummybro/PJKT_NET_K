"""One entry point: create the local environment, install dependencies, start everything."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def dependencies_ready(python):
    check = "import importlib.metadata as m, pathlib; rows=pathlib.Path('requirements-lock.txt').read_text().splitlines(); assert all(m.version(n)==v for line in rows if line.strip() and not line.startswith('#') for n,v in [line.split('==',1)])"
    return subprocess.run([str(python), '-c', check], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup-only',action='store_true')
    args, runtime_args=parser.parse_known_args()
    if sys.version_info < (3,10):
        raise RuntimeError('Python 3.10 or newer is required; Python 3.11+ is recommended.')
    python=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    print('Network Knight - setup and start',flush=True)
    if not python.exists():
        print('[1/3] Creating the project Python environment...',flush=True)
        subprocess.run([sys.executable,'-m','venv',str(ROOT/'.venv')],check=True,cwd=ROOT)
    else:print('[1/3] Python environment found.',flush=True)
    if not dependencies_ready(python):
        print('[2/3] Installing required packages. Internet is needed for this step...',flush=True)
        subprocess.run([str(python),'-m','pip','install','-r','requirements-lock.txt'],check=True,cwd=ROOT)
        if not dependencies_ready(python):raise RuntimeError('Package verification failed. Review pip output above.')
    else:print('[2/3] Required packages verified; no installation needed.',flush=True)
    if args.setup_only:
        print('Setup complete. Use Start-Network-Knight.cmd to launch all components.',flush=True)
        return 0
    print('[3/3] Starting the dashboard, protection monitor and Windows logging...',flush=True)
    return subprocess.call([str(python),'run.py',*runtime_args],cwd=ROOT)

if __name__=='__main__':
    try:sys.exit(main())
    except KeyboardInterrupt:
        print('Network Knight was stopped by you.',flush=True)
        sys.exit(0)
    except (OSError,RuntimeError,subprocess.CalledProcessError) as exc:
        print('SETUP/START FAILED:',exc,flush=True)
        print('Check Python installation, internet access and the error above. No monitoring success is assumed.',flush=True)
        sys.exit(1)
