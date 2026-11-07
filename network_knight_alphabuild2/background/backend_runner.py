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
    logging.config.dictConfig(config)
    class LogStream:
        def write(self, text):
            if text.strip():
                logging.getLogger('supervisor').info(text.strip())
        def flush(self): pass
    sys.stdout = LogStream()
    sys.stderr = LogStream()
    os.environ['NETWORK_KNIGHT_BACKGROUND'] = '1'
    from backend.app import app
    from backend.service_control import Supervisor
    app.state.runtime = Supervisor(ROOT / 'backend/data', 'http://127.0.0.1:8787')
    uvicorn.run(app, host='127.0.0.1', port=8787, log_config=None, access_log=False)
