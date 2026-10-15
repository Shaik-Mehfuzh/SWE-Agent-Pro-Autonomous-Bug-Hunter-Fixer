import unittest
from paginator import QuerySet

class TestQuerySetPagination(unittest.TestCase):
    def setUp(self):
        self.qs = QuerySet(range(30))

    def test_count(self):
        self.assertEqual(self.qs.count(), 30)

    def test_page_1(self):
        res = self.qs.paginate(page=1, page_size=10)
        self.assertEqual(res, list(range(0, 10)))

    def test_page_2(self):
        res = self.qs.paginate(page=2, page_size=10)
        self.assertEqual(res, list(range(10, 20)))

if __name__ == "__main__":
    unittest.main()
