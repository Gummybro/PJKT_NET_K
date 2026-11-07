from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import bootstrap


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='backend/tests')
        self.root=Path(self.tmp.name).resolve()
        python=self.root/'.venv'/('Scripts/python.exe' if bootstrap.os.name=='nt' else 'bin/python')
        python.parent.mkdir(parents=True)
        python.touch()

    def tearDown(self): self.tmp.cleanup()

    def test_verified_install_launches_without_network_or_reinstall(self):
        with patch.object(bootstrap,'ROOT',self.root), patch.object(bootstrap,'dependencies_ready',return_value=True), \
             patch.object(bootstrap.sys,'argv',['bootstrap.py','--no-browser']), \
             patch.object(bootstrap.subprocess,'run') as install, patch.object(bootstrap.subprocess,'call',return_value=0) as start:
            self.assertEqual(bootstrap.main(),0)
            install.assert_not_called()
            self.assertIn('--no-browser',start.call_args.args[0])

    def test_install_failure_never_reports_or_launches_monitoring(self):
        with patch.object(bootstrap,'ROOT',self.root), patch.object(bootstrap,'dependencies_ready',return_value=False), \
             patch.object(bootstrap.sys,'argv',['bootstrap.py']), \
             patch.object(bootstrap.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'pip')), \
             patch.object(bootstrap.subprocess,'call') as start:
            with self.assertRaises(subprocess.CalledProcessError):bootstrap.main()
            start.assert_not_called()


if __name__=='__main__':unittest.main()
