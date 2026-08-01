import unittest
import subprocess
import time
import sys
from pathlib import Path

class TestSyncLock(unittest.TestCase):
    def test_concurrent_sync(self):
        """
        Lanza dos procesos de sincronización casi simultáneamente
        y verifica que el segundo falle con exit code 3 (ALREADY_RUNNING).
        """
        project_dir = Path(__file__).resolve().parent.parent
        sync_script = project_dir / "backend" / "fechas_sync.py"
        
        # Lanzar primer proceso
        p1 = subprocess.Popen(
            [sys.executable, str(sync_script), "--dry-run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Esperar un instante pequeñísimo para asegurar que p1 arranca primero
        time.sleep(0.5)
        
        # Lanzar segundo proceso
        p2 = subprocess.Popen(
            [sys.executable, str(sync_script), "--dry-run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Esperar a que terminen
        out1, err1 = p1.communicate(timeout=30)
        out2, err2 = p2.communicate(timeout=30)
        
        # Verificar que uno terminó con 0 y el otro con 3
        exit_codes = [p1.returncode, p2.returncode]
        
        self.assertIn(0, exit_codes, "Al menos un proceso debió tener éxito (código 0)")
        self.assertIn(3, exit_codes, "El segundo proceso debió fallar por lock (código 3)")
        self.assertNotEqual(p1.returncode, p2.returncode, "Ambos procesos no deben tener el mismo código")

if __name__ == '__main__':
    unittest.main()
