"""Unit tests for the pure, dependency-free helpers in app.text."""
import unittest

from app.text import (
    build_context,
    chunk_words,
    make_run_id,
    section_heading,
    slugify,
    vector_literal,
)


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Data Retention Policy"), "data-retention-policy")

    def test_strips_special_chars(self):
        self.assertEqual(slugify("  Security & Compliance! "), "security-compliance")


class TestSectionHeading(unittest.TestCase):
    def test_numbered_heading(self):
        self.assertEqual(
            section_heading("3.2 Data Retention\nsome body text"),
            "3.2 Data Retention",
        )

    def test_all_caps_heading(self):
        self.assertEqual(section_heading("DATA RETENTION\nbody"), "DATA RETENTION")

    def test_plain_text_has_no_heading(self):
        self.assertIsNone(section_heading("just a normal paragraph with no heading at all"))


class TestChunkWords(unittest.TestCase):
    def test_small_input_single_chunk(self):
        chunks = chunk_words("one two three".split(), page_number=3, section="S")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["page_number"], 3)
        self.assertEqual(chunks[0]["section_heading"], "S")

    def test_overlap_produces_multiple_chunks(self):
        words = [str(i) for i in range(100)]
        chunks = chunk_words(words, None, None, size=60, overlap=20)
        self.assertGreater(len(chunks), 1)

    def test_empty_input(self):
        self.assertEqual(chunk_words([], None, None), [])


class TestVectorLiteral(unittest.TestCase):
    def test_format(self):
        self.assertEqual(vector_literal([1.0, 2.5, 0.0]), "[1.0,2.5,0.0]")

    def test_integer_floats(self):
        self.assertEqual(vector_literal([1, 2]), "[1,2]")


class TestRunId(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(make_run_id("t1", "q"), make_run_id("t1", "q"))

    def test_differs_by_question(self):
        self.assertNotEqual(make_run_id("t1", "q1"), make_run_id("t1", "q2"))

    def test_differs_by_thread(self):
        self.assertNotEqual(make_run_id("t1", "q"), make_run_id("t2", "q"))


class TestBuildContext(unittest.TestCase):
    def test_page_none_renders_na(self):
        chunks = [
            {
                "title": "P",
                "version": 2,
                "page_number": None,
                "section_heading": "Data Retention",
                "text": "hello world",
                "chunk_id": "c1",
            }
        ]
        context, citations = build_context(chunks)
        self.assertIn("page n/a", context)
        self.assertIn('section "Data Retention"', context)
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["index"], 1)
        self.assertIsNone(citations[0]["page"])
        self.assertEqual(citations[0]["chunk_id"], "c1")

    def test_page_number_preserved(self):
        chunks = [
            {
                "title": "P",
                "version": 1,
                "page_number": 4,
                "section_heading": None,
                "text": "hello",
                "chunk_id": "c2",
            }
        ]
        context, citations = build_context(chunks)
        self.assertIn("page 4", context)
        self.assertEqual(citations[0]["page"], 4)


if __name__ == "__main__":
    unittest.main()
