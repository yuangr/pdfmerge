import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject, TextStringObject

from pdf_operations import (
    ensure_output_is_separate, export_reordered, format_groups, merge_pdfs,
    parse_groups, read_pdf, validate_groups, write_atomic,
)


def sample_pdf(count=12):
    writer = PdfWriter()
    for number in range(1, count + 1):
        page = writer.add_blank_page(width=200 + number, height=400 + number)
        page.rotate((number % 4) * 90)
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 10 100 Td (PAGE_{number}) Tj ET".encode("ascii"))
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_metadata({"/Title": "Reorder fixture", "/Author": "Local test"})
    writer.add_outline_item("First section", 0)
    if count >= 9:
        writer.add_outline_item("Third section", 8)
        internal_link = writer.add_annotation(0, Link(rect=(0, 0, 20, 20), target_page_index=8))
        # Local PDF destinations reference a page object, not an integer index.
        internal_link["/Dest"][0] = writer.pages[8].indirect_reference
    writer.add_annotation(0, Link(rect=(20, 20, 40, 40), url="https://example.com/"))
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class PdfOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.pdf"
        self.data = sample_pdf()
        self.source.write_bytes(self.data)
        self.output = self.root / "result.pdf"

    def test_reorder_preserves_all_page_content_geometry_rotation_and_metadata(self):
        groups = parse_groups("9-12,1-3,4-8", 12)
        export_reordered(self.data, self.source, groups, self.output)
        reader = PdfReader(self.output)
        expected = list(range(9, 13)) + list(range(1, 9))
        self.assertEqual([p.extract_text() for p in reader.pages], [f"PAGE_{n}" for n in expected])
        self.assertEqual([float(p.mediabox.width) for p in reader.pages], [200 + n for n in expected])
        self.assertEqual([float(p.mediabox.height) for p in reader.pages], [400 + n for n in expected])
        self.assertEqual([p.rotation for p in reader.pages], [(n % 4) * 90 for n in expected])
        self.assertEqual(reader.metadata.title, "Reorder fixture")
        self.assertEqual(self.source.read_bytes(), self.data)

    def test_bookmarks_and_links_follow_reordered_pages(self):
        export_reordered(self.data, self.source, [(8, 12), (0, 8)], self.output)
        reader = PdfReader(self.output)
        outlines = {item.title: reader.get_destination_page_number(item) for item in reader.outline if not isinstance(item, list)}
        self.assertEqual(outlines, {"First section": 4, "Third section": 0})
        annotations = [ref.get_object() for ref in reader.pages[4]["/Annots"]]
        internal = next(item for item in annotations if "/Dest" in item)
        self.assertEqual(internal["/Dest"][0], reader.pages[0].indirect_reference)
        external = next(item for item in annotations if "/A" in item)
        self.assertEqual(external["/A"]["/URI"], "https://example.com/")

    def test_form_values_follow_their_page(self):
        writer = PdfWriter()
        writer.add_blank_page(200, 300)
        writer.add_blank_page(300, 400)
        field = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"): NameObject("/Tx"),
            NameObject("/T"): TextStringObject("name"),
            NameObject("/V"): TextStringObject("example"),
            NameObject("/Rect"): ArrayObject([NumberObject(10), NumberObject(10), NumberObject(100), NumberObject(40)]),
        })
        field_ref = writer._add_object(field)
        writer.pages[0][NameObject("/Annots")] = ArrayObject([field_ref])
        writer.root_object[NameObject("/AcroForm")] = DictionaryObject({NameObject("/Fields"): ArrayObject([field_ref])})
        buffer = io.BytesIO()
        writer.write(buffer)
        export_reordered(buffer.getvalue(), self.source, [(1, 2), (0, 1)], self.output)
        reader = PdfReader(self.output)
        self.assertEqual(reader.get_form_text_fields(), {"name": "example"})
        self.assertEqual(reader.pages[1]["/Annots"][0].get_object()["/V"], "example")

    def test_mixed_single_pages_and_chinese_separators(self):
        groups = parse_groups(" 7，1–6；8-12 ", 12)
        self.assertEqual(validate_groups(groups, 12), (6, 0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11))
        self.assertEqual(format_groups(groups), "7,1-6,8-12")

    def test_invalid_ranges_are_rejected(self):
        invalid = ["1-11", "1-12,1", "0-12", "1-13", "3-1,4-12", "1-12,", "hello", "", "1.5-12"]
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_groups(text, 12)

    def test_invalid_plan_never_replaces_existing_output(self):
        self.output.write_bytes(b"existing output")
        with self.assertRaises(ValueError):
            export_reordered(self.data, self.source, [(0, 11)], self.output)
        self.assertEqual(self.output.read_bytes(), b"existing output")

    def test_source_overwrite_is_rejected(self):
        with self.assertRaises(ValueError):
            export_reordered(self.data, self.source, [(0, 12)], self.source)
        self.assertEqual(self.source.read_bytes(), self.data)

    def test_hardlink_to_source_is_rejected(self):
        os.link(self.source, self.output)
        with self.assertRaises(ValueError):
            ensure_output_is_separate(self.output, (self.source,))
        self.assertEqual(self.source.read_bytes(), self.data)

    def test_partial_write_keeps_old_output_and_cleans_temp_file(self):
        self.output.write_bytes(b"old output")
        writer = PdfWriter()
        writer.add_blank_page(100, 100)

        def partial(stream):
            stream.write(b"partial")
            raise OSError("simulated disk failure")

        with patch.object(writer, "write", side_effect=partial), self.assertRaises(OSError):
            write_atomic(writer, self.output, (self.source,), 1)
        self.assertEqual(self.output.read_bytes(), b"old output")
        self.assertEqual(list(self.root.glob(".pdfmerge-*.pdf")), [])

    def test_page_count_failure_keeps_old_output(self):
        self.output.write_bytes(b"old output")
        writer = PdfWriter()
        writer.add_blank_page(100, 100)
        with self.assertRaises(ValueError):
            write_atomic(writer, self.output, (self.source,), 2)
        self.assertEqual(self.output.read_bytes(), b"old output")
        self.assertEqual(list(self.root.glob(".pdfmerge-*.pdf")), [])

    def test_existing_destination_is_replaced_with_valid_pdf(self):
        self.output.write_bytes(b"old output")
        export_reordered(self.data, self.source, [(0, 12)], self.output)
        self.assertEqual(len(PdfReader(self.output).pages), 12)
        self.assertEqual(list(self.root.glob(".pdfmerge-*.pdf")), [])

    def test_single_page_pdf(self):
        data = sample_pdf(1)
        export_reordered(data, self.source, parse_groups("1", 1), self.output)
        self.assertEqual(PdfReader(self.output).pages[0].extract_text(), "PAGE_1")

    def test_merge_still_follows_file_order(self):
        other = self.root / "other.pdf"
        other.write_bytes(sample_pdf(2))
        merge_pdfs((other, self.source), self.output)
        reader = PdfReader(self.output)
        self.assertEqual(len(reader.pages), 14)
        self.assertEqual([p.extract_text() for p in reader.pages[:4]], ["PAGE_1", "PAGE_2", "PAGE_1", "PAGE_2"])
        self.assertEqual(self.source.read_bytes(), self.data)

    def test_password_and_invalid_pdf_fail_before_export(self):
        with self.assertRaises(Exception):
            read_pdf(b"not a PDF")
        writer = PdfWriter()
        writer.add_blank_page(100, 100)
        writer.encrypt("secret-for-test")
        buffer = io.BytesIO()
        writer.write(buffer)
        with self.assertRaisesRegex(ValueError, "需要密码"):
            read_pdf(buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
