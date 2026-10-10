"""PDF operations independent of the desktop interface."""

import io
import os
import re
import tempfile
from collections import Counter

from pypdf import PdfReader, PdfWriter


def read_pdf(data):
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("此 PDF 需要密码，请先使用 PDF 阅读器解密并另存，再导入。")
    if not reader.pages:
        raise ValueError("PDF 中没有页面。")
    return reader


def validate_groups(groups, page_count):
    if page_count < 1 or not groups:
        raise ValueError("请先导入含有页面的 PDF。")
    counts = Counter()
    for start, stop in groups:
        if not (0 <= start < stop <= page_count):
            raise ValueError(f"页码超出范围或页段倒置；有效页码为 1–{page_count}。")
        counts.update(range(start, stop))
    missing = [page + 1 for page in range(page_count) if counts[page] == 0]
    repeated = [page + 1 for page in range(page_count) if counts[page] > 1]
    problems = []
    if missing:
        problems.append("遗漏页码：" + ", ".join(map(str, missing[:12])) + ("…" if len(missing) > 12 else ""))
    if repeated:
        problems.append("重复页码：" + ", ".join(map(str, repeated[:12])) + ("…" if len(repeated) > 12 else ""))
    if problems:
        raise ValueError("；".join(problems) + "。完整重排要求每个原始页面恰好出现一次。")
    return tuple(page for start, stop in groups for page in range(start, stop))


def parse_groups(text, page_count):
    text = text.strip()
    if not text:
        raise ValueError("请输入页段，例如：1-3,4-8,9-12。")
    tokens = re.split(r"[,，;；\n]+", text)
    groups = []
    for token in tokens:
        match = re.fullmatch(r"\s*([0-9]+)\s*(?:[-–—]\s*([0-9]+)\s*)?", token)
        if not match:
            raise ValueError(f"无法识别页段“{token.strip()}”；请用逗号分隔单页或连续页段。")
        first = int(match.group(1))
        last = int(match.group(2) or first)
        groups.append((first - 1, last))
    validate_groups(groups, page_count)
    return groups


def format_groups(groups):
    return ",".join(str(start + 1) if stop == start + 1 else f"{start + 1}-{stop}" for start, stop in groups)


def ensure_output_is_separate(output_path, source_paths):
    output = os.path.normcase(os.path.realpath(os.path.abspath(output_path)))
    for source in source_paths:
        source_real = os.path.normcase(os.path.realpath(os.path.abspath(source)))
        same_file = output == source_real
        if not same_file and os.path.exists(output_path) and os.path.exists(source):
            same_file = os.path.samefile(output_path, source)
        if same_file:
            raise ValueError("保存位置不能是原始 PDF，请选择新的文件名。")


def write_atomic(writer, output_path, source_paths, expected_pages):
    """Replace the destination only after a complete, readable PDF is ready."""
    output_path = os.path.abspath(output_path)
    ensure_output_is_separate(output_path, source_paths)
    directory = os.path.dirname(output_path)
    os.makedirs(directory, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".pdfmerge-", suffix=".pdf", dir=directory, delete=False) as stream:
            temporary = stream.name
            writer.write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        with open(temporary, "rb") as stream:
            if len(PdfReader(stream).pages) != expected_pages:
                raise ValueError("导出后的页数校验失败，未替换目标文件。")
        ensure_output_is_separate(output_path, source_paths)
        os.replace(temporary, output_path)
        temporary = None
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def export_reordered(data, source_path, groups, output_path):
    reader = read_pdf(data)
    order = validate_groups(groups, len(reader.pages))
    with PdfWriter() as writer:
        writer.append(reader, pages=list(order))
        if reader.metadata:
            writer.add_metadata(reader.metadata)
        write_atomic(writer, output_path, (source_path,), len(order))


def merge_pdfs(source_paths, output_path):
    source_paths = tuple(source_paths)
    if not source_paths:
        raise ValueError("请先选择需要合并的 PDF 文件。")
    ensure_output_is_separate(output_path, source_paths)
    with PdfWriter() as writer:
        for path in source_paths:
            with open(path, "rb") as stream:
                reader = read_pdf(stream.read())
            writer.append(reader)
        write_atomic(writer, output_path, source_paths, len(writer.pages))
