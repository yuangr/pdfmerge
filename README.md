# PDF 极速合并工具 (PDF Merger Tool)

一款基于 Python `CustomTkinter` 和 `pypdf` 构建的、具有 **Linear 极客暗黑风格** 的本地 PDF 合并桌面工具。

## 🌟 功能特点
- **Linear 暗黑美学**: 极简深灰底色，微发光分割板块，搭配紫罗兰品牌色（`#5E6AD2`）高亮及精致按钮反馈。
- **直观列表操作**: 支持添加多个 PDF 文件，提供 `▲` / `▼` 按钮进行顺序调整，支持单项移出及清空。
- **一键另存为**: 合并输出集成 Windows 原生“另存为”对话框，支持智能文件名补全（无 `.pdf` 后缀自动追加）。
- **异步后台合并**: 采用多线程合并技术，合并大文件不卡顿，完成后支持一键直接打开生成的 PDF。
- **设计规范契约**: 包含符合 Google Labs 规范的 [DESIGN.md](DESIGN.md) 视觉规范。

## 📂 项目结构
- `pdf_merger_gui.py`: 主程序源码。
- `DESIGN.md`: 设计规范契约文件。
- `run_pdf_merger.bat`: 快捷启动批处理（双击隐藏控制台运行）。

## 🚀 运行方法
1. 确保安装了 Python 3.8+。
2. 安装依赖：
   ```bash
   pip install customtkinter pypdf pyinstaller
   ```
3. 运行主程序：
   ```bash
   python pdf_merger_gui.py
   ```
4. 打包可执行程序（可选）：
   ```bash
   pyinstaller --onefile --windowed --collect-all customtkinter pdf_merger_gui.py
   ```

## ⚖️ 许可与使用说明
**本程序仅用于个人测试和使用，未经版权所有者明确授权，严禁用于任何商业用途！** 详见 [LICENSE](LICENSE) 文件。
