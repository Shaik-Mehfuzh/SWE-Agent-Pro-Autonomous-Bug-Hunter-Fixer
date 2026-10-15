import unittest
from config_loader import load_setting, list_keys

class TestConfigLoader(unittest.TestCase):
    def test_load_existing(self):
        self.assertEqual(load_setting({"port": 8080}, "port", 3000), 8080)

    def test_load_none_config(self):
        self.assertEqual(load_setting(None, "port", 3000), 3000)

    def test_list_keys(self):
        self.assertEqual(list_keys({"a": 1, "b": 2}), ["a", "b"])

if __name__ == "__main__":
    unittest.main()
