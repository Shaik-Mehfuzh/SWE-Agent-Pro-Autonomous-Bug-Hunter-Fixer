"""
QuerySet pagination implementation
"""

class QuerySet:
    def __init__(self, items):
        self.items = list(items)

    def count(self):
        return len(self.items)

    def paginate(self, page=1, page_size=10):
        """
        Paginates dataset.
        Expects 1-indexed page (page=1 is first page).
        """
        # Defect: 1-based page without subtraction skips first items on page 2+
        offset = page * page_size
        return self.items[offset : offset + page_size]
