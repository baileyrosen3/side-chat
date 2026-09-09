import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import install
import setup
from jarvis import settings
from jarvis import setup as speech_setup


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in (("platform.system", "Linux"), ("platform.machine", "x86_64"),
                            ("os.geteuid", 1000)):
            self.stack.enter_context(patch("setup." + name, return_value=value))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.stack.enter_context(contextlib.redirect_stderr(io.StringIO()))

    def test_check_reports_missing_requirements_without_mutations(self):
        with patch("setup.shutil.which", return_value="/bin/tool"), \
             patch("setup.missing_packages", return_value=["qt6-quick3d"]), \
             patch("setup.agent_problem", return_value="Choose an agent"), \
             patch("setup.runtime_problems", return_value=["No runtime"]), \
             patch("setup.input_problems", return_value=["No uinput"]), \
             patch("setup.run") as mutate, patch("setup.install_input_access") as permissions, \
             patch("setup.subprocess.run") as child:
            self.assertEqual(setup.main(["--check", "--with-desktop-input"]), 1)
            mutate.assert_not_called()
            permissions.assert_not_called()
            child.assert_not_called()

    def test_chat_only_installs_missing_packages_without_voice_or_input(self):
        with patch("setup.shutil.which", return_value="/bin/tool"), \
             patch("setup.missing_packages", return_value=["qt6-quick3d"]), \
             patch("setup.agent_problem", return_value=None), \
             patch("setup.run") as mutate, patch("setup.install_input_access") as permissions:
            self.assertEqual(setup.main([]), 0)
            mutate.assert_called_once_with(["omarchy", "pkg", "add", "qt6-quick3d"])
            permissions.assert_not_called()

    def test_optional_engines_forward_to_speech_setup(self):
        with patch("setup.shutil.which", return_value="/bin/tool"), \
             patch("setup.missing_packages", return_value=[]) as packages, \
             patch("setup.agent_problem", return_value=None), \
             patch("setup.runtime_problems", return_value=[]), \
             patch("setup.subprocess.run", return_value=subprocess.CompletedProcess([], 1)), \
             patch("setup.run") as mutate, patch("setup.install_input_access") as permissions:
            self.assertEqual(setup.main(["--with-kokoro", "--with-legacy-asr"]), 0)
            packages.assert_called_once_with(True)
            command = mutate.call_args.args[0]
            self.assertEqual(command[-2:], ["--with-kokoro", "--with-legacy-asr"])
            self.assertEqual(Path(command[2]), setup.SOURCE / "jarvis/setup.py")
            permissions.assert_not_called()

    def test_active_voice_blocks_runtime_replacement(self):
        with patch("setup.shutil.which", return_value="/bin/tool"), \
             patch("setup.missing_packages", return_value=[]), \
             patch("setup.subprocess.run", return_value=subprocess.CompletedProcess(
                 [], 0, '{"jarvis":{"enabled":true}}')), patch("setup.run") as mutate:
            for flag in ('--with-peek','--with-jarvis'):
                with self.subTest(flag=flag),self.assertRaisesRegex(SystemExit, "power Peek off"):
                    setup.main([flag])
            mutate.assert_not_called()

    def test_package_failure_stops_before_downloads(self):
        with patch("setup.shutil.which", return_value="/bin/tool"), \
             patch("setup.missing_packages", return_value=["chromium"]), \
             patch("setup.run", side_effect=subprocess.CalledProcessError(1, "omarchy")) as mutate:
            with self.assertRaises(subprocess.CalledProcessError):
                setup.main(["--with-jarvis"])
            self.assertEqual(mutate.call_count, 1)

    def test_reuses_existing_tools_and_skips_installed_packages(self):
        def query(command, **kwargs):
            return subprocess.CompletedProcess(command, int(command[-1] == "chromium"))
        with patch("setup.shutil.which", return_value="/mise/tool"), \
             patch("setup.subprocess.run", side_effect=query) as queried:
            self.assertEqual(setup.missing_packages(True), ["chromium"])
            packages = [call.args[0][-1] for call in queried.call_args_list]
            self.assertNotIn("rust", packages)
            self.assertNotIn("uv", packages)

    def test_missing_tools_are_included_for_clean_voice_install(self):
        with patch("setup.shutil.which", return_value=None), \
             patch("setup.subprocess.run", return_value=subprocess.CompletedProcess([], 1)):
            missing = setup.missing_packages(True)
            self.assertIn("rust", missing)
            self.assertIn("uv", missing)
            self.assertIn("python-gobject", missing)

    def test_unsupported_architecture_stops_before_installs(self):
        with patch("setup.platform.machine", return_value="aarch64"), patch("setup.run") as mutate:
            with self.assertRaises(SystemExit):
                setup.main(["--with-jarvis"])
            mutate.assert_not_called()

    def test_git_checkout_and_symlink_are_never_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "plugin"
            destination.mkdir()
            (destination / ".git").mkdir()
            (destination / "keep").write_text("user data")
            with self.assertRaisesRegex(SystemExit, "Git-managed"):
                install.check_destination(destination)
            link = Path(folder) / "link"
            link.symlink_to(destination)
            with self.assertRaises(SystemExit):
                install.check_destination(link)
            self.assertEqual((destination / "keep").read_text(), "user data")

    def test_incomplete_shared_model_uses_private_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shared = root / "voxtype/models/parakeet-unified-en-0.6b"
            shared.mkdir(parents=True)
            with patch.object(settings, "DATA_HOME", root), patch.object(settings, "DATA", root / "side-chat"):
                private = root / "side-chat/models/parakeet-unified-en-0.6b"
                self.assertEqual(settings.model_path(settings.DEFAULTS), private)
                for name in ("encoder.onnx", "encoder.onnx.data", "decoder_joint.onnx", "tokenizer.model"):
                    (shared / name).write_bytes(b"fixture")
                self.assertEqual(settings.model_path(settings.DEFAULTS), shared)
                self.assertEqual(settings.model_path({"modelPath": str(private)}), private)

    def test_build_prerequisites_checked_before_downloading(self):
        with patch("jarvis.setup.shutil.which", side_effect=lambda name: None if name == "cargo" else "/bin/tool"):
            with self.assertRaisesRegex(SystemExit, "Missing build tools: cargo"):
                speech_setup.preflight()

    def test_copy_distribution_contains_setup_and_pinned_sources(self):
        expected = {"setup.py", "jarvis/setup.py", "jarvis/parakeet/Cargo.lock",
                    "jarvis/requirements-legacy.txt", "docs/publishing.md", *setup.INPUT_FILES}
        self.assertTrue(expected.issubset(install.FILES))
        for name in install.FILES:
            self.assertTrue((setup.SOURCE / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
