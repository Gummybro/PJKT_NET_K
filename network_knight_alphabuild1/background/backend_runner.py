"""Windowless entry point for the Windows scheduled backend task."""
import logging.config
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
# This computer's project-local dependencies; normal ZIP setups use .venv.
if (ROOT / '.python-packages').is_dir():
    sys.path.insert(0, str(ROOT / '.python-packages'))
os.environ['NETWORK_KNIGHT_DATA'] = str(ROOT / 'backend' / 'data')
logs = ROOT / 'backend' / 'data' / 'background'
logs.mkdir(parents=True, exist_ok=True)

if __name__ == '__main__':
    import uvicorn
    config = {
        'version': 1, 'disable_existing_loggers': False,
        'formatters': {'plain': {'format': '%(asctime)s %(levelname)s %(name)s %(message)s'}},
        'handlers': {'file': {'class': 'logging.handlers.RotatingFileHandler',
                             'filename': str(logs / 'backend.log'), 'maxBytes': 2097152,
                             'backupCount': 3, 'encoding': 'utf-8', 'formatter': 'plain'}},
        'root': {'handlers': ['file'], 'level': 'INFO'},
        'loggers': {'uvicorn': {'handlers': ['file'], 'level': 'INFO', 'propagate': False},
                    'uvicorn.error': {'level': 'INFO'},
                    'uvicorn.access': {'handlers': ['file'], 'level': 'INFO', 'propagate': False}},
    }
    uvicorn.run('backend.app:app', host='127.0.0.1', port=8787, log_config=config)
