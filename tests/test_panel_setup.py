import unittest
from panel_setup import panel_config


class PanelSetupTests(unittest.TestCase):
    def test_service_entry_moves_with_settings_and_preserves_island(self):
        source = {"bar": {"id": "blr.island", "layout": {"left": [{"id": "blr.den"}]},
                          "settings": {"hiddenScreens": ["FLIP4"]}},
                  "plugins": [{"id": "blr.side-chat", "custom": 7}, {"id": "mirador"}]}
        result = panel_config(source)
        self.assertEqual(result["bar"]["layout"]["left"], [{"id": "blr.den"}, {"id": "blr.side-chat", "custom": 7}])
        self.assertEqual(result["bar"]["settings"], source["bar"]["settings"])
        self.assertEqual(result["plugins"], [{"id": "mirador"}])
        self.assertEqual(len(source["plugins"]), 2)
        self.assertEqual(panel_config(result), result)

    def test_existing_widget_keeps_placement_and_no_duplicate_service(self):
        source = {"bar": {"layout": {"right": [{"id": "blr.side-chat", "size": "small"}]}},
                  "plugins": ["blr.side-chat"], "disabledPlugins": ["other", "blr.side-chat"]}
        result = panel_config(source)
        self.assertEqual(result["bar"]["layout"]["right"], source["bar"]["layout"]["right"])
        self.assertEqual(result["bar"]["layout"]["left"], [])
        self.assertEqual(result["plugins"], [])
        self.assertEqual(result["disabledPlugins"], ["other"])

    def test_new_install_has_a_single_widget(self):
        result = panel_config({})
        self.assertEqual(result["bar"]["layout"]["left"], [{"id": "blr.side-chat"}])
        self.assertEqual(panel_config(result), result)
