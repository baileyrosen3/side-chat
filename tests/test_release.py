import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def test_manifest_is_the_runtime_version_source(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")

        main = (ROOT / "Main.qml").read_text()
        self.assertIn("property var manifest:", main)
        self.assertIn("readonly property string uiVersion:", main)
        self.assertIn("uiVersion:root.uiVersion", main)
        self.assertNotRegex(main, r'uiVersion\s*:\s*"\d+\.\d+\.\d+"')

    def test_preferences_exposes_the_loaded_version(self):
        window = (ROOT / "ChatWindow.qml").read_text()
        self.assertIn('text: "Side Chat " + chat.uiVersion', window)
        self.assertIn('Accessible.name: "Installed Side Chat version " + chat.uiVersion', window)

    def test_readme_uses_noninteractive_trusted_update_and_live_check(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("omarchy plugin update blr.side-chat --yes", readme)
        self.assertIn("omarchy-shell blr.side-chat status | jq", readme)
        self.assertIn("That diff is terminal output, not a file or an error.", readme)


if __name__ == "__main__":
    unittest.main()
