import os
from pathlib import Path
import tempfile
import threading
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from pypdf import PdfReader

from pdf_merger_gui import PDFMergerApp
from pdf_operations import merge_pdfs as actual_merge
from test_pdf_operations import sample_pdf


class PageOrganizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = PDFMergerApp()
        cls.app.withdraw()
        cls.app.update()

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source.pdf"
        self.data = sample_pdf()
        self.source.write_bytes(self.data)
        self.organizer = self.app.page_organizer
        self.organizer.source_path = str(self.source)
        self.organizer.source_data = self.data
        self.organizer.page_count = 12
        self.organizer.groups = [(n, n + 1) for n in range(12)]
        self.organizer.output_var.set(str(Path(self.temp.name) / "out.pdf"))
        self.organizer.render()
        self.app.mode_switch.set("页面整理")
        self.app.switch_mode("页面整理")

    def wait_for(self, predicate):
        deadline = time.monotonic() + 10
        while not predicate() and time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.01)
        self.assertTrue(predicate(), "background job timed out")

    def select(self, index):
        self.organizer.page_list.selection_clear(0, tk.END)
        self.organizer.page_list.selection_set(index)

    def apply(self, text):
        self.organizer.ranges_entry.delete(0, tk.END)
        self.organizer.ranges_entry.insert(0, text)
        self.organizer.apply_groups()

    def test_import_runs_worker_and_populates_page_list(self):
        self.organizer.source_data = None
        with patch("page_organizer.filedialog.askopenfilename", return_value=str(self.source)), patch("page_organizer.messagebox.showerror") as error:
            self.organizer.load_source()
            self.assertTrue(self.organizer.busy)
            self.wait_for(lambda: not self.organizer.busy)
            error.assert_not_called()
        self.assertEqual(self.organizer.page_list.size(), 12)
        self.assertEqual(self.organizer.output_var.get(), str(self.source.with_name("source_重排.pdf")))

    def test_group_move_split_restore_and_target_position(self):
        self.apply("1-3,4-8,9-12")
        self.select(2)
        self.organizer.move_relative(-1)
        self.organizer.move_relative(-1)
        self.assertEqual(self.organizer.groups, [(8, 12), (0, 3), (3, 8)])
        self.assertIn("输出第 1–4 页", self.organizer.page_list.get(0))
        self.assertIn("原第 9–12 页", self.organizer.page_list.get(0))
        with patch("page_organizer.simpledialog.askinteger", return_value=3):
            self.organizer.move_to_position()
        self.assertEqual(self.organizer.groups, [(0, 3), (3, 8), (8, 12)])
        self.organizer.split_selected()
        self.assertEqual(self.organizer.groups[2:], [(8, 9), (9, 10), (10, 11), (11, 12)])
        with patch("page_organizer.messagebox.askyesno", return_value=True):
            self.organizer.restore_order()
        self.assertEqual(self.organizer.groups, [(n, n + 1) for n in range(12)])

    def test_pending_and_invalid_ranges_do_not_change_plan(self):
        previous = list(self.organizer.groups)
        self.organizer.ranges_entry.delete(0, tk.END)
        self.organizer.ranges_entry.insert(0, "1-11")
        with patch("page_organizer.messagebox.showinfo") as info:
            self.organizer.move_relative(1)
            info.assert_called_once()
        with patch("page_organizer.messagebox.showerror") as error:
            self.organizer.apply_groups()
            error.assert_called_once()
        self.assertEqual(self.organizer.groups, previous)

    def test_background_export_and_controls_lock(self):
        self.apply("9-12,1-3,4-8")
        with patch("page_organizer.messagebox.askyesno", return_value=False), patch("page_organizer.messagebox.showerror") as error:
            self.organizer.start_export()
            self.assertTrue(self.organizer.busy)
            self.assertEqual(self.app.mode_switch.cget("state"), "disabled")
            self.assertEqual(self.organizer.export_btn.cget("state"), "disabled")
            before = list(self.organizer.groups)
            self.organizer.move_relative(1)
            self.assertEqual(self.organizer.groups, before)
            self.wait_for(lambda: not self.organizer.busy)
            error.assert_not_called()
        result = PdfReader(self.organizer.output_var.get())
        self.assertEqual([p.extract_text() for p in result.pages[:4]], ["PAGE_9", "PAGE_10", "PAGE_11", "PAGE_12"])
        self.assertEqual(self.app.mode_switch.cget("state"), "normal")

    def test_mode_switch_preserves_independent_lists(self):
        self.app.selected_files = [str(self.source)]
        self.app.update_file_list_ui()
        self.apply("9-12,1-8")
        self.app.switch_mode("文件合并")
        self.app.switch_mode("页面整理")
        self.assertEqual(self.app.selected_files, [str(self.source)])
        self.assertEqual(self.organizer.groups, [(8, 12), (0, 8)])

    def test_merge_freezes_input_and_restores_controls(self):
        self.app.selected_files = [str(self.source)]
        self.app.update_file_list_ui()
        output = str(Path(self.temp.name) / "merged.pdf")
        self.app.set_save_path(output)
        gate = threading.Event()
        self.addCleanup(gate.set)
        captured = []

        def merge(paths, destination):
            captured.append(paths)
            gate.wait(5)
            actual_merge(paths, destination)

        with patch("pdf_merger_gui.merge_pdfs", side_effect=merge), patch("pdf_merger_gui.messagebox.askyesno", return_value=False):
            self.app.start_merge()
            self.assertTrue(self.app.is_merging)
            self.assertEqual(self.app.add_btn.cget("state"), "disabled")
            self.app.remove_file(0)
            self.assertEqual(self.app.selected_files, [str(self.source)])
            gate.set()
            self.wait_for(lambda: not self.app.is_merging)
        self.assertEqual(captured, [(str(self.source),)])
        self.assertEqual(len(PdfReader(output).pages), 12)
        self.assertEqual(self.app.add_btn.cget("state"), "normal")

    def test_failed_import_retains_previous_document(self):
        corrupt = Path(self.temp.name) / "corrupt.pdf"
        corrupt.write_bytes(b"invalid")
        previous = list(self.organizer.groups)
        with patch("page_organizer.filedialog.askopenfilename", return_value=str(corrupt)), patch("page_organizer.messagebox.askyesno", return_value=True), patch("page_organizer.messagebox.showerror") as error:
            self.organizer.load_source()
            self.wait_for(lambda: not self.organizer.busy)
            error.assert_called_once()
        self.assertEqual(self.organizer.source_data, self.data)
        self.assertEqual(self.organizer.groups, previous)


if __name__ == "__main__":
    unittest.main()
