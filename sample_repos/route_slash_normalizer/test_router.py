import unittest
from route_matcher import match_endpoint, get_base_path

class TestRouteMatcher(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(match_endpoint("/api/v1/users", "/api/v1/users"))

    def test_trailing_slash_normalization(self):
        self.assertTrue(match_endpoint("/api/v1/users/", "/api/v1/users"))

    def test_base_path(self):
        self.assertEqual(get_base_path("/api/v1/users"), "/api")

if __name__ == "__main__":
    unittest.main()
