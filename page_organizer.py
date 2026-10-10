"""Arrange all pages of a single PDF without intermediate PDF files."""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from pdf_operations import (
    ensure_output_is_separate, export_reordered, format_groups,
    parse_groups, read_pdf, validate_groups,
)


class PageOrganizer(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color=app.c_bg_primary)
        self.app = app
        self.source_path = ""
        self.source_data = None
        self.page_count = 0
        self.groups = []
        self.applied_text = ""
        self.busy = False
        self.events = queue.Queue()
        self.controls = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        source_bar = ctk.CTkFrame(self, fg_color="transparent")
        source_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        source_bar.grid_columnconfigure(0, weight=1)
        self.source_label = ctk.CTkLabel(source_bar, text="导入一份 PDF，调整页面或页段顺序", anchor="w", wraplength=510, text_color=app.c_text_secondary)
        self.source_label.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.button(source_bar, "导入 PDF", self.load_source, primary=True).grid(row=0, column=1)

        group_bar = ctk.CTkFrame(self, fg_color=app.c_bg_secondary, corner_radius=8)
        group_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        group_bar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(group_bar, text="页段按原始页码填写，例如 1-3,4-8,9-12；应用后可整段移动", anchor="w", text_color=app.c_text_secondary).grid(row=0, column=0, columnspan=2, padx=12, pady=(8, 2), sticky="w")
        self.ranges_entry = ctk.CTkEntry(group_bar, placeholder_text="单页或连续页段，用逗号分隔", height=32)
        self.ranges_entry.grid(row=1, column=0, padx=12, pady=(2, 12), sticky="ew")
        self.controls.append(self.ranges_entry)
        self.button(group_bar, "应用页段", self.apply_groups).grid(row=1, column=1, padx=(0, 12), pady=(2, 12))

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        toolbar.grid_columnconfigure(4, weight=1)
        self.button(toolbar, "上移", lambda: self.move_relative(-1), width=65).grid(row=0, column=0, padx=(0, 6))
        self.button(toolbar, "下移", lambda: self.move_relative(1), width=65).grid(row=0, column=1, padx=(0, 6))
        self.button(toolbar, "移到位置…", self.move_to_position, width=100).grid(row=0, column=2, padx=(0, 6))
        self.button(toolbar, "拆为单页", self.split_selected, width=90).grid(row=0, column=3)
        self.button(toolbar, "恢复原序", self.restore_order, width=90).grid(row=0, column=5)

        list_frame = ctk.CTkFrame(self, fg_color=app.c_bg_secondary, border_width=1, border_color=app.c_border, corner_radius=8)
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)
        self.count_label = ctk.CTkLabel(list_frame, text="尚未导入 PDF", anchor="w", text_color=app.c_text_secondary)
        self.count_label.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=5)
        self.page_list = tk.Listbox(
            list_frame, bg=app.c_bg_secondary, fg=app.c_text_primary,
            selectbackground=app.c_brand, selectforeground="white",
            activestyle="none", exportselection=False, selectmode=tk.BROWSE,
            borderwidth=0, highlightthickness=0, font=("Segoe UI", 12), height=8,
        )
        self.page_list.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 12))
        scrollbar = ctk.CTkScrollbar(list_frame, command=self.page_list.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 5), pady=(0, 12))
        self.page_list.configure(yscrollcommand=scrollbar.set)
        self.page_list.bind("<Alt-Up>", lambda event: self.move_relative(-1))
        self.page_list.bind("<Alt-Down>", lambda event: self.move_relative(1))

        output = ctk.CTkFrame(self, fg_color=app.c_bg_secondary, corner_radius=8)
        output.grid(row=4, column=0, sticky="ew", pady=(12, 8))
        output.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(output, text="保存为：", text_color=app.c_text_primary).grid(row=0, column=0, padx=12, pady=12)
        self.output_var = tk.StringVar()
        self.output_entry = ctk.CTkEntry(output, textvariable=self.output_var, state="readonly")
        self.output_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=12)
        self.button(output, "选择位置…", self.choose_output).grid(row=0, column=2, padx=(0, 12), pady=12)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=5, column=0, sticky="ew")
        actions.grid_columnconfigure(0, weight=1)
        self.status = ctk.CTkLabel(actions, text="每个原始页面保留一次；导出不会修改页面中的印刷页码。", anchor="w", text_color=app.c_text_muted, wraplength=490)
        self.status.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.export_btn = self.button(actions, "导出重排 PDF", self.start_export, primary=True, width=160)
        self.export_btn.grid(row=0, column=1, sticky="e", pady=5)
        self.after(100, self.poll_events)

    def button(self, parent, text, command, primary=False, width=100):
        button = ctk.CTkButton(parent, text=text, command=command, width=width, height=32,
                               fg_color=self.app.c_brand if primary else self.app.c_bg_active,
                               hover_color=self.app.c_brand_hover if primary else self.app.c_border_light)
        self.controls.append(button)
        return button

    def set_status(self, text, error=False):
        self.status.configure(text=text, text_color=self.app.c_error if error else self.app.c_text_secondary)

    def set_busy(self, busy):
        self.busy = busy
        for control in self.controls:
            control.configure(state="disabled" if busy else "normal")
        self.page_list.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.app.mode_switch.configure(state="disabled" if busy else "normal")

    def launch(self, operation, work):
        self.set_busy(True)
        self.set_status("正在读取 PDF…" if operation == "load" else "正在导出并校验 PDF…")

        def worker():
            try:
                self.events.put((operation, work(), None))
            except Exception as error:
                self.events.put((operation, None, str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def poll_events(self):
        try:
            operation, result, error = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.set_busy(False)
            if error:
                self.set_status("读取失败" if operation == "load" else "导出失败", error=True)
                messagebox.showerror("页面整理", error, parent=self.app)
            elif operation == "load":
                self.source_path, self.source_data, self.page_count = result
                self.groups = [(page, page + 1) for page in range(self.page_count)]
                self.source_label.configure(text=f"{os.path.basename(self.source_path)}  ·  {self.page_count} 页")
                self.output_var.set(os.path.splitext(self.source_path)[0] + "_重排.pdf")
                self.render(0)
                self.set_status("已按单页载入；选中后移动，或填写页段后点击应用。")
            else:
                self.set_status(f"导出成功：{os.path.basename(result)}")
                if messagebox.askyesno("导出完成", f"完整 PDF 已保存，共 {self.page_count} 页。\n\n{result}\n\n是否打开？", parent=self.app):
                    try:
                        os.startfile(result)
                    except OSError as error:
                        messagebox.showerror("打开失败", str(error), parent=self.app)
        self.after(100, self.poll_events)

    def load_source(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(title="导入需要重排的完整 PDF", filetypes=[("PDF 文件", "*.pdf")], parent=self.app)
        if not path:
            return
        if self.source_data is not None and not messagebox.askyesno("更换 PDF", "更换文件将清除当前的页面排列，是否继续？", parent=self.app):
            return
        path = os.path.abspath(path)

        def load():
            with open(path, "rb") as stream:
                data = stream.read()
            return path, data, len(read_pdf(data).pages)

        self.launch("load", load)

    def ready(self, check_pending=True):
        if self.busy:
            return False
        if self.source_data is None:
            messagebox.showinfo("页面整理", "请先导入一份 PDF。", parent=self.app)
            return False
        if check_pending and self.ranges_entry.get().strip() != self.applied_text:
            messagebox.showinfo("页段尚未应用", "页段输入已修改，请先点击“应用页段”。", parent=self.app)
            return False
        return True

    def render(self, selected=0):
        self.page_list.delete(0, tk.END)
        output_page = 1
        rows = []
        for number, (start, stop) in enumerate(self.groups, 1):
            length = stop - start
            original = str(start + 1) if length == 1 else f"{start + 1}–{stop}"
            destination = str(output_page) if length == 1 else f"{output_page}–{output_page + length - 1}"
            rows.append(f"{number:03d}    输出第 {destination} 页    ←    原第 {original} 页")
            output_page += length
        if rows:
            self.page_list.insert(tk.END, *rows)
            selected = min(max(selected, 0), len(self.groups) - 1)
            self.page_list.selection_set(selected)
            self.page_list.activate(selected)
            self.page_list.see(selected)
        self.applied_text = format_groups(self.groups)
        self.ranges_entry.delete(0, tk.END)
        self.ranges_entry.insert(0, self.applied_text)
        self.count_label.configure(text=f"原始 {self.page_count} 页  ·  输出 {output_page - 1} 页  ·  {len(self.groups)} 个单页 / 页段")

    def apply_groups(self):
        if not self.ready(check_pending=False):
            return
        try:
            groups = parse_groups(self.ranges_entry.get(), self.page_count)
        except ValueError as error:
            messagebox.showerror("页段无效", str(error), parent=self.app)
            return
        self.groups = groups
        self.render()
        self.set_status("页段已应用；可选中整段移动，所有原始页面均保留一次。")

    def selected_index(self):
        if not self.ready():
            return None
        selected = self.page_list.curselection()
        if not selected:
            messagebox.showinfo("页面整理", "请先选中需要操作的单页或页段。", parent=self.app)
            return None
        return selected[0]

    def move_relative(self, offset):
        index = self.selected_index()
        if index is not None and 0 <= index + offset < len(self.groups):
            group = self.groups.pop(index)
            self.groups.insert(index + offset, group)
            self.render(index + offset)
            self.set_status("顺序已调整，导出时按列表从上到下排列。")
        return "break"

    def move_to_position(self):
        index = self.selected_index()
        if index is None:
            return
        target = simpledialog.askinteger("移动到位置", f"输入目标列表位置（1–{len(self.groups)}），不是原始页码：", initialvalue=index + 1, minvalue=1, maxvalue=len(self.groups), parent=self.app)
        if target is not None:
            group = self.groups.pop(index)
            self.groups.insert(target - 1, group)
            self.render(target - 1)
            self.set_status("顺序已调整，导出时按列表从上到下排列。")

    def split_selected(self):
        index = self.selected_index()
        if index is not None:
            start, stop = self.groups[index]
            self.groups[index:index + 1] = [(page, page + 1) for page in range(start, stop)]
            self.render(index)
            self.set_status("所选页段已拆为单页，可分别调整位置。")

    def restore_order(self):
        if not self.ready(check_pending=False):
            return
        if messagebox.askyesno("恢复原序", "恢复原始页面顺序，并重置为逐页排列？", parent=self.app):
            self.groups = [(page, page + 1) for page in range(self.page_count)]
            self.render()
            self.set_status("已恢复原始页面顺序。")

    def choose_output(self):
        if not self.ready(check_pending=False):
            return
        current = self.output_var.get()
        path = filedialog.asksaveasfilename(title="另存重排后的完整 PDF", initialdir=os.path.dirname(current), initialfile=os.path.basename(current), defaultextension=".pdf", filetypes=[("PDF 文件", "*.pdf")], parent=self.app)
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.output_var.set(os.path.abspath(path))

    def start_export(self):
        if not self.ready():
            return
        output = self.output_var.get().strip()
        if not output:
            messagebox.showerror("页面整理", "请选择保存位置。", parent=self.app)
            return
        groups = tuple(self.groups)
        try:
            validate_groups(groups, self.page_count)
            ensure_output_is_separate(output, (self.source_path,))
        except ValueError as error:
            messagebox.showerror("无法导出", str(error), parent=self.app)
            return
        if os.path.exists(output) and not messagebox.askyesno("替换文件", f"目标文件已存在，是否替换？\n\n{output}", parent=self.app):
            return
        data, source = self.source_data, self.source_path

        def export():
            export_reordered(data, source, groups, output)
            return output

        self.launch("export", export)
