# PDF 合并与页面整理

基于 Python、CustomTkinter 和 pypdf 的本地 Windows 桌面工具。

当前版本：**v1.1.0**。从 [GitHub Releases](https://github.com/yuangr/pdfmerge/releases) 下载 `PDF.exe`，双击即可运行，无需安装 Python。更新内容见 [CHANGELOG.md](CHANGELOG.md)。

## 页面整理：调整一份完整 PDF 的页序

1. 双击 Release 中下载的 `PDF.exe`；从源码运行时可使用 `run_pdf_merger.bat` 或本地打包的 `dist/pdf_merger_gui.exe`。
2. 在“页面整理”中导入一份 PDF，默认按单页列出。
3. 选中单页，点击“上移”“下移”或“移到位置…”调整顺序。
4. 如果需要整段移动，在页段框填写 `1-3,4-8,9-12`，点击“应用页段”，再调整整段的位置。也可直接输入完整的新顺序，如 `9-12,1-3,4-8`。
5. “拆为单页”将选中页段展开为单页；“恢复原序”恢复原始逐页排列。
6. 选择保存位置，点击“导出重排 PDF”，另存为一份完整文档。

列表同时显示输出页码和原始页码。页段输入修改后必须先应用，才能移动或导出。单页和页段可混用，每个原始页面必须恰好出现一次；遗漏、重复、倒置和越界页码均会被拒绝。所有页码均指从 1 开始的物理页面序号，而非 PDF 页面标签或页面上印刷的页码。重排不会自动改写印刷页码。

处理全部在本地完成，不产生中间拆分 PDF。不支持密码输入，需要密码的文档请先解密另存。当前采用页码列表，不包含缩略图预览和鼠标拖拽。

## 文件合并

切换到“文件合并”，添加多个 PDF，通过 ▲ / ▼ 排序，可移出文件或清空列表，然后另存合并结果。相同路径只添加一次。

两种模式都禁止输出覆盖输入 PDF。后台处理时固定本次输入并禁用编辑；先写临时文件并验证页数，再替换目标文件。已有目标文件需要确认替换。处理过程中需等待完成后关闭窗口。

## 开发与运行

本项目已在 Python 3.11 环境验证；安装依赖：

```bash
pip install customtkinter pypdf pyinstaller
python pdf_merger_gui.py
```

`run_pdf_merger.bat` 使用项目 `.venv` 中的 Python 隐藏控制台运行。

打包：

```bash
pyinstaller --noconfirm --onefile --windowed --collect-all customtkinter pdf_merger_gui.py
```

测试：

```bash
python -m unittest discover -s tests -v
```

## 项目结构

- `pdf_merger_gui.py`：主窗口和文件合并界面。
- `page_organizer.py`：单份 PDF 的页面 / 页段整理界面。
- `pdf_operations.py`：页段解析、完整性校验、PDF 重排和安全导出。
- `tests/`：导出顺序、页面特征、异常路径与界面交互验证。
- `DESIGN.md`：现有暗色视觉规范。

## 许可

本程序仅用于个人测试和使用，未经版权所有者明确授权，严禁用于任何商业用途。详见 `LICENSE`。
