import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
import zipfile

from app.updater import (
    UpdateError,
    _installer_script_text,
    _payload_root,
    _safe_extract,
    consume_update_result,
    is_newer_version,
)


class UpdaterTests(unittest.TestCase):
    def test_semantic_version_comparison(self) -> None:
        self.assertTrue(is_newer_version("v1.1.0", "1.0.9"))
        self.assertFalse(is_newer_version("v1.0.0", "1.0"))
        self.assertFalse(is_newer_version("invalid", "1.0.0"))

    def test_payload_root_accepts_single_distribution_folder(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "AstralOptimizer"
            payload.mkdir()
            (payload / "AstralOptimizer.exe").touch()
            self.assertEqual(_payload_root(root), payload)

    def test_safe_extract_rejects_parent_traversal(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../outside.txt", "danger")
            with self.assertRaises(UpdateError):
                _safe_extract(archive, root / "output")

    def test_installer_script_retries_validates_and_records_result(self) -> None:
        script = _installer_script_text()
        self.assertIn("tentativa $attempt de 3", script)
        self.assertIn("$sourceExe.Length -ne $targetExe.Length", script)
        self.assertIn("Write-UpdateResult 'success'", script)
        self.assertIn("Write-UpdateResult 'error'", script)

    def test_consumes_successful_update_result(self) -> None:
        with TemporaryDirectory() as directory:
            result = Path(directory) / "update-result.json"
            result.write_text(
                '{"status":"success","version":"1.2.1",'
                '"message":"Atualizado","log_path":"update.log"}',
                encoding="utf-8",
            )
            parsed = consume_update_result(result)
            self.assertIsNotNone(parsed)
            assert parsed is not None
            self.assertEqual(parsed.status, "success")
            self.assertEqual(parsed.version, "1.2.1")
            self.assertFalse(result.exists())

    @unittest.skipUnless(os.name == "nt", "O instalador automático é exclusivo do Windows")
    def test_powershell_installer_replaces_files_and_writes_log(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "origem com espaços"
            target = root / "destino com espaços"
            state = root / "estado da atualização"
            source.mkdir()
            target.mkdir()
            state.mkdir()
            (source / "AstralOptimizer.exe").write_bytes(b"novo-executavel-1.2.1")
            (target / "AstralOptimizer.exe").write_bytes(b"executavel-antigo")
            (source / "version.json").write_text(
                json.dumps({"version": "1.2.1"}), encoding="utf-8"
            )
            (source / "novo-arquivo.txt").write_text("copiado", encoding="utf-8")
            script = root / "apply-update.ps1"
            script.write_text(_installer_script_text(), encoding="utf-8-sig")
            result_file = state / "update-result.json"
            log_file = state / "update-v1.2.1.log"

            process = subprocess.run(
                [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(script), "-AppProcessId", "2147483647",
                    "-Source", str(source), "-Target", str(target),
                    "-Executable", "AstralOptimizer.exe", "-Version", "1.2.1",
                    "-ResultFile", str(result_file), "-LogFile", str(log_file),
                    "-SkipRestart",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            self.assertEqual(process.returncode, 0, process.stderr or process.stdout)
            self.assertEqual(
                (target / "AstralOptimizer.exe").read_bytes(),
                b"novo-executavel-1.2.1",
            )
            self.assertEqual(
                (target / "novo-arquivo.txt").read_text("utf-8"), "copiado"
            )
            self.assertEqual(
                json.loads(result_file.read_text("utf-8-sig"))["status"], "success"
            )
            self.assertIn("aplicada com sucesso", log_file.read_text("utf-8-sig"))

    @unittest.skipUnless(os.name == "nt", "O instalador automático é exclusivo do Windows")
    def test_powershell_installer_records_failure_without_valid_payload(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "origem vazia"
            target = root / "destino"
            state = root / "estado"
            source.mkdir()
            target.mkdir()
            state.mkdir()
            script = root / "apply-update.ps1"
            script.write_text(_installer_script_text(), encoding="utf-8-sig")
            result_file = state / "update-result.json"
            log_file = state / "update.log"

            process = subprocess.run(
                [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(script), "-AppProcessId", "2147483647",
                    "-Source", str(source), "-Target", str(target),
                    "-Executable", "AstralOptimizer.exe", "-Version", "1.2.1",
                    "-ResultFile", str(result_file), "-LogFile", str(log_file),
                    "-SkipRestart",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            self.assertNotEqual(process.returncode, 0)
            result = json.loads(result_file.read_text("utf-8-sig"))
            self.assertEqual(result["status"], "error")
            self.assertIn("não foi encontrado", result["message"])
            self.assertIn("ERRO:", log_file.read_text("utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
