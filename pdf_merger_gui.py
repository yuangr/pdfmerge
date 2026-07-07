import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from pypdf import PdfWriter

# Lock appearance mode to dark theme for unified Linear aesthetic
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class PDFMergerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("PDF 极速合并工具")
        self.geometry("760x640")
        self.minsize(680, 520)
        
        # Color Tokens (Linear Dark Theme)
        self.c_bg_primary = "#0B0B0C"
        self.c_bg_secondary = "#161618"
        self.c_bg_active = "#252529"
        
        self.c_brand = "#5E6AD2"
        self.c_brand_hover = "#707EE6"
        self.c_brand_active = "#4D58B2"
        
        self.c_text_primary = "#F4F4F5"
        self.c_text_secondary = "#A1A1AA"
        self.c_text_muted = "#71717A"
        
        self.c_border = "#27272A"
        self.c_border_light = "#2D2D31"
        
        self.c_success = "#4ADE80"
        self.c_error = "#F87171"
        self.c_error_bg = "#351616"
        self.c_error_border = "#522020"
        self.c_error_hover = "#4D1D1D"

        # Apply root background
        self.configure(fg_color=self.c_bg_primary)
        
        self.selected_files = []
        
        # Configure grid layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Header Frame (Blended with window background)
        self.header_frame = ctk.CTkFrame(self, fg_color=self.c_bg_primary, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="PDF 极速合并工具", 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=self.c_text_primary
        )
        self.title_label.grid(row=0, column=0, padx=25, pady=(25, 5), sticky="w")
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame, 
            text="极客风格的 PDF 合并小工具。选择文件，自由排序，一键合并。",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=self.c_text_secondary
        )
        self.subtitle_label.grid(row=1, column=0, padx=25, pady=(0, 20), sticky="w")
        
        # 2. Main content area
        self.main_frame = ctk.CTkFrame(self, fg_color=self.c_bg_primary)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=(0, 15))
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1) # File list row expands
        
        # File list section header & buttons
        self.list_header_frame = ctk.CTkFrame(self.main_frame, fg_color=self.c_bg_primary)
        self.list_header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.list_header_frame.grid_columnconfigure(0, weight=1)
        
        self.list_title = ctk.CTkLabel(
            self.list_header_frame, 
            text="待合并文件列表", 
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=self.c_text_primary
        )
        self.list_title.grid(row=0, column=0, sticky="w")
        
        self.add_btn = ctk.CTkButton(
            self.list_header_frame, 
            text="+ 添加 PDF 文件", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=135,
            height=32,
            fg_color=self.c_brand,
            hover_color=self.c_brand_hover,
            text_color=self.c_text_primary,
            corner_radius=8,
            command=self.add_files
        )
        self.add_btn.grid(row=0, column=1, padx=(5, 5), sticky="e")
        
        self.clear_btn = ctk.CTkButton(
            self.list_header_frame, 
            text="清空列表", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=85,
            height=32,
            fg_color=self.c_error_bg,
            hover_color=self.c_error_hover,
            text_color=self.c_error,
            border_color=self.c_error_border,
            border_width=1,
            corner_radius=8,
            command=self.clear_files
        )
        self.clear_btn.grid(row=0, column=2, sticky="e")
        
        # Scrollable file list frame
        self.file_list_frame = ctk.CTkScrollableFrame(
            self.main_frame, 
            label_text="",
            fg_color=self.c_bg_secondary,
            border_color=self.c_border,
            border_width=1,
            corner_radius=12
        )
        self.file_list_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        
        # Placeholder when list is empty
        self.empty_label = ctk.CTkLabel(
            self.file_list_frame, 
            text="暂未添加文件，请点击上方“添加 PDF 文件”按钮",
            text_color=self.c_text_muted,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.empty_label.pack(expand=True, fill="both", pady=120)
        
        # 3. Output Configuration Frame
        self.output_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=self.c_bg_secondary,
            border_color=self.c_border,
            border_width=1,
            corner_radius=12
        )
        self.output_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0), padx=2)
        self.output_frame.grid_columnconfigure(1, weight=1)
        
        self.save_label = ctk.CTkLabel(
            self.output_frame, 
            text="保存路径:", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.c_text_primary
        )
        self.save_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.save_path_entry = ctk.CTkEntry(
            self.output_frame, 
            placeholder_text="请选择保存路径及文件名",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=self.c_bg_primary,
            border_color=self.c_border,
            border_width=1,
            text_color=self.c_text_primary,
            placeholder_text_color=self.c_text_muted,
            corner_radius=8
        )
        self.save_path_entry.grid(row=0, column=1, padx=(0, 15), pady=20, sticky="ew")
        self.save_path_entry.configure(state="readonly")
        
        self.save_btn = ctk.CTkButton(
            self.output_frame, 
            text="选择位置...", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=110,
            height=32,
            fg_color=self.c_bg_active,
            hover_color=self.c_border_light,
            text_color=self.c_text_primary,
            border_color=self.c_border,
            border_width=1,
            corner_radius=8,
            command=self.choose_save_path
        )
        self.save_btn.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="e")
        
        # 4. Action Frame (Merge Button and Progress)
        self.action_frame = ctk.CTkFrame(self, fg_color=self.c_bg_primary)
        self.action_frame.grid(row=2, column=0, sticky="ew", padx=25, pady=(5, 25))
        self.action_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            self.action_frame, 
            text="就绪", 
            text_color=self.c_text_muted,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.status_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.merge_btn = ctk.CTkButton(
            self.action_frame, 
            text="开始合并 PDF", 
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            height=42,
            width=190,
            fg_color=self.c_brand,
            hover_color=self.c_brand_hover,
            text_color=self.c_text_primary,
            corner_radius=8,
            command=self.start_merge
        )
        self.merge_btn.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
    def add_files(self):
        file_paths = filedialog.askopenfilenames(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if file_paths:
            for path in file_paths:
                normalized_path = os.path.abspath(path)
                if normalized_path not in self.selected_files:
                    self.selected_files.append(normalized_path)
            
            # Set default save path if none is currently selected
            if not self.save_path_entry.get() and self.selected_files:
                first_file_dir = os.path.dirname(self.selected_files[0])
                first_file_name = os.path.basename(self.selected_files[0])
                name_without_ext, _ = os.path.splitext(first_file_name)
                default_save_path = os.path.join(first_file_dir, f"{name_without_ext}_合并.pdf")
                self.set_save_path(default_save_path)
                
            self.update_file_list_ui()
            self.update_status(f"已添加 {len(file_paths)} 个文件。当前共 {len(self.selected_files)} 个文件。")
            
    def clear_files(self):
        if self.selected_files:
            if messagebox.askyesno("清空列表", "确定要清空待合并的文件列表吗？"):
                self.selected_files.clear()
                self.update_file_list_ui()
                self.set_save_path("")
                self.update_status("已清空列表")
                
    def choose_save_path(self):
        initial_dir = None
        initial_file = "合并文件_合并.pdf"
        
        # Check if we have an existing path in entry to use as initial values
        current_val = self.save_path_entry.get()
        if current_val:
            initial_dir = os.path.dirname(current_val)
            initial_file = os.path.basename(current_val)
        elif self.selected_files:
            initial_dir = os.path.dirname(self.selected_files[0])
            first_file_name = os.path.basename(self.selected_files[0])
            name_without_ext, _ = os.path.splitext(first_file_name)
            initial_file = f"{name_without_ext}_合并.pdf"
            
        file_path = filedialog.asksaveasfilename(
            title="选择保存位置及输入文件名",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=".pdf",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if file_path:
            # Check if file has .pdf extension, if not, append it
            if not file_path.lower().endswith(".pdf"):
                file_path += ".pdf"
            normalized_path = os.path.abspath(file_path)
            self.set_save_path(normalized_path)
            self.update_status(f"保存位置已选择")

    def set_save_path(self, path):
        self.save_path_entry.configure(state="normal")
        self.save_path_entry.delete(0, tk.END)
        self.save_path_entry.insert(0, path)
        self.save_path_entry.configure(state="readonly")
            
    def move_file_up(self, index):
        if index > 0:
            self.selected_files[index], self.selected_files[index - 1] = \
                self.selected_files[index - 1], self.selected_files[index]
            self.update_file_list_ui()
            
    def move_file_down(self, index):
        if index < len(self.selected_files) - 1:
            self.selected_files[index], self.selected_files[index + 1] = \
                self.selected_files[index + 1], self.selected_files[index]
            self.update_file_list_ui()
            
    def remove_file(self, index):
        if 0 <= index < len(self.selected_files):
            removed = self.selected_files.pop(index)
            self.update_file_list_ui()
            self.update_status(f"已移出文件: {os.path.basename(removed)}")
            
    def update_file_list_ui(self):
        # Clear existing children from the scrollable frame
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
            
        if not self.selected_files:
            self.empty_label = ctk.CTkLabel(
                self.file_list_frame, 
                text="暂未添加文件，请点击上方“添加 PDF 文件”按钮",
                text_color=self.c_text_muted,
                font=ctk.CTkFont(family="Segoe UI", size=13)
            )
            self.empty_label.pack(expand=True, fill="both", pady=120)
            return
            
        # Draw each file item
        for i, file_path in enumerate(self.selected_files):
            # Panel card for list item
            item_frame = ctk.CTkFrame(
                self.file_list_frame, 
                height=50,
                fg_color=self.c_bg_primary,
                border_color=self.c_border_light,
                border_width=1,
                corner_radius=8
            )
            item_frame.pack(fill="x", padx=10, pady=5)
            item_frame.pack_propagate(False)
            
            # Number label
            num_label = ctk.CTkLabel(
                item_frame, 
                text=f"{i+1:02d}", 
                width=35, 
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=self.c_brand
            )
            num_label.pack(side="left", padx=(15, 5))
            
            # File name and path
            filename = os.path.basename(file_path)
            file_label = ctk.CTkLabel(
                item_frame, 
                text=filename, 
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal"),
                text_color=self.c_text_primary
            )
            file_label.pack(side="left", fill="x", expand=True, padx=5)
            
            # Action buttons
            btn_frame = ctk.CTkFrame(item_frame, fg_color=self.c_bg_primary)
            btn_frame.pack(side="right", padx=10)
            
            up_btn = ctk.CTkButton(
                btn_frame, 
                text="▲", 
                width=32, 
                height=26,
                fg_color=self.c_bg_active,
                hover_color=self.c_border_light,
                text_color=self.c_text_secondary if i > 0 else self.c_text_muted,
                state="normal" if i > 0 else "disabled",
                corner_radius=6,
                command=lambda idx=i: self.move_file_up(idx)
            )
            up_btn.pack(side="left", padx=2)
            
            down_btn = ctk.CTkButton(
                btn_frame, 
                text="▼", 
                width=32, 
                height=26,
                fg_color=self.c_bg_active,
                hover_color=self.c_border_light,
                text_color=self.c_text_secondary if i < len(self.selected_files) - 1 else self.c_text_muted,
                state="normal" if i < len(self.selected_files) - 1 else "disabled",
                corner_radius=6,
                command=lambda idx=i: self.move_file_down(idx)
            )
            down_btn.pack(side="left", padx=2)
            
            del_btn = ctk.CTkButton(
                btn_frame, 
                text="✕", 
                width=32, 
                height=26,
                fg_color=self.c_error_bg,
                hover_color=self.c_error_hover,
                text_color=self.c_error,
                corner_radius=6,
                command=lambda idx=i: self.remove_file(idx)
            )
            del_btn.pack(side="left", padx=(8, 2))

    def update_status(self, text, color=None):
        if color is None:
            color = self.c_text_muted
        elif color == "blue":
            color = self.c_brand
        elif color == "green":
            color = self.c_success
        elif color == "red":
            color = self.c_error
            
        self.status_label.configure(text=text, text_color=color)
        
    def start_merge(self):
        if not self.selected_files:
            messagebox.showerror("错误", "请先选择需要合并的 PDF 文件！")
            return
            
        output_path = self.save_path_entry.get().strip()
        
        if not output_path:
            messagebox.showerror("错误", "请选择保存路径及文件名！")
            return
            
        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"
            
        # Disable merge button and show loading state
        self.merge_btn.configure(state="disabled", text="正在合并...")
        self.update_status("正在合并 PDF，请稍候...", "blue")
        
        # Start backend merge thread
        thread = threading.Thread(target=self.execute_merge, args=(output_path,))
        thread.daemon = True
        thread.start()
        
    def execute_merge(self, output_path):
        try:
            # Ensure the output directory exists
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # Perform PDF merge
            merger = PdfWriter()
            for file_path in self.selected_files:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"文件不存在: {file_path}")
                merger.append(file_path)
                
            merger.write(output_path)
            merger.close()
            
            # Show success status on main thread
            self.after(0, lambda: self.on_merge_success(output_path))
            
        except Exception as e:
            # Show error status on main thread
            self.after(0, lambda err=str(e): self.on_merge_failure(err))
            
    def on_merge_success(self, output_path):
        self.merge_btn.configure(state="normal", text="开始合并 PDF")
        self.update_status(f"合并成功！保存至: {os.path.basename(output_path)}", "green")
        
        # Ask user if they want to open the merged file
        if messagebox.askyesno("成功", f"合并成功！\n是否打开合并后的 PDF 文件？\n\n路径: {output_path}"):
            try:
                os.startfile(output_path)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件: {e}")
                
    def on_merge_failure(self, error_message):
        self.merge_btn.configure(state="normal", text="开始合并 PDF")
        self.update_status("合并失败！", "red")
        messagebox.showerror("合并失败", f"合并过程中发生错误：\n{error_message}")

if __name__ == "__main__":
    app = PDFMergerApp()
    app.mainloop()
