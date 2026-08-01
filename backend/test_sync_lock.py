import unittest
import subprocess
import sys
import os
import tempfile
from pathlib import Path

class TestSyncLock(unittest.TestCase):
    def test_concurrent_sync(self):
        """
        Bloquea intencionalmente el archivo .sync.lock en un entorno aislado temporal
        y verifica que fechas_sync.py devuelva exit code 3 (ALREADY_RUNNING).
        """
        project_dir = Path(__file__).resolve().parent.parent
        sync_script = project_dir / "backend" / "fechas_sync.py"
        
        with tempfile.TemporaryDirectory() as temp_home:
            # Set up fake HOME
            env = os.environ.copy()
            env["HOME"] = temp_home
            
            # 1. Crear el directorio app_data
            app_data_dir = Path(temp_home) / ".local" / "share" / "fechas-academicas"
            app_data_dir.mkdir(parents=True, exist_ok=True)
            lock_file_path = app_data_dir / "sync.lock"
            
            # Script python para adquirir el lock y quedarse esperando
            lock_holder_code = f"""
import fcntl
import time
with open('{lock_file_path}', 'w') as f:
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    print("READY", flush=True)
    time.sleep(60)
"""
            p_holder = None
            try:
                # Lanzar el proceso que retiene el lock
                p_holder = subprocess.Popen(
                    [sys.executable, "-c", lock_holder_code],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )
                
                # Esperar hasta que avise que ya tiene el lock
                ready = p_holder.stdout.readline()
                self.assertEqual(ready.strip(), "READY")
                
                # Lanzar fechas_sync.py, el cual debería fallar
                p_sync = subprocess.run(
                    [sys.executable, str(sync_script), "--dry-run"],
                    capture_output=True,
                    env=env
                )
                
                # Debe retornar 3
                self.assertEqual(p_sync.returncode, 3, "El script debió abortar con código 3 porque el lock estaba tomado.")
            finally:
                if p_holder:
                    p_holder.terminate()
                    p_holder.wait(timeout=5)
                    if p_holder.stdout:
                        p_holder.stdout.close()
                    if p_holder.stderr:
                        p_holder.stderr.close()

if __name__ == '__main__':
    unittest.main()
