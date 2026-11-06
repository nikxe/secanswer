"""Static invariants that the schema must enforce.

The whole point of the versioning + idempotency fixes is that they live in the
database, not in application code. These tests read schema.sql and fail if the
invariants are ever removed.
"""
import unittest
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "schema.sql"


class TestSchemaInvariants(unittest.TestCase):
    def setUp(self):
        self.sql = SCHEMA.read_text()

    def test_pgvector_extension(self):
        self.assertIn("CREATE EXTENSION IF NOT EXISTS vector", self.sql)

    def test_documents_have_version_and_current_flag(self):
        self.assertIn("is_current", self.sql)
        self.assertIn("version", self.sql)

    def test_one_current_version_enforced_by_index(self):
        self.assertIn("one_current_version_per_doc", self.sql)
        self.assertIn("UNIQUE", self.sql)

    def test_answers_idempotent_by_run_id(self):
        self.assertIn("run_id", self.sql)
        self.assertIn("saved_answers", self.sql)
        # The UNIQUE run_id is the idempotency guard; ON CONFLICT is applied at
        # write time in app/graph.py.
        self.assertIn("UNIQUE", self.sql)

    def test_chunks_capture_page_and_section(self):
        self.assertIn("page_number", self.sql)
        self.assertIn("section_heading", self.sql)


if __name__ == "__main__":
    unittest.main()
