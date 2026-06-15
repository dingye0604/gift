#!/usr/bin/env python3
"""Gift 项目构建脚本：从 content/ 下的 .tex 文件生成 LaTeX 书稿 PDF 和静态网站。"""

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# ── 路径配置 ────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"

# 部署目标
#   "github" → dingye0604.github.io/gift（子目录，BASE_URL = "/gift"）
#   "local"   → 本地预览（根路径，BASE_URL = ""）
TARGET = "github"
BASE_URL = "/gift" if TARGET == "github" else ""
BOOK_DIR = ROOT / "book"
SITE_DIR = ROOT / "site"
OUTPUT_DIR = ROOT / "output"
SITE_OUTPUT = SITE_DIR / "output"

DYNASTIES = [
    ("先秦", "xian-qin"),
    ("两汉", "liang-han"),
    ("魏晋", "wei-jin"),
    ("南北朝", "nan-bei-chao"),
    ("唐", "tang"),
    ("五代十国", "wudai-shiguo"),
    ("两宋", "liang-song"),
    ("元", "yuan"),
    ("明清", "ming-qing"),
    ("近代", "jin-dai"),
]


# ── .tex 解析 ───────────────────────────────────────
def parse_tex(filepath: Path) -> dict | None:
    """解析单个 .tex 内容文件，返回元信息、诗歌正文、赏析正文。"""
    text = filepath.read_text(encoding="utf-8")

    meta = {}
    for m in re.finditer(r"^%\s*!(\w+)\s+(.+)$", text, re.MULTILINE):
        meta[m.group(1).lower()] = m.group(2).strip()

    if "title" not in meta:
        return None

    poem = ""
    pm = re.search(r"\\begin\{poem\}\s*\n(.*?)\n\s*\\end\{poem\}", text, re.DOTALL)
    if pm:
        poem = pm.group(1).strip()

    appreciation = ""
    am = re.search(
        r"\\begin\{appreciation\}\s*\n(.*?)\n\s*\\end\{appreciation\}",
        text,
        re.DOTALL,
    )
    if am:
        appreciation = am.group(1).strip()

    annotations = []
    nm = re.search(
        r"\\begin\{annotations\}\s*\n(.*?)\\end\{annotations\}",
        text,
        re.DOTALL,
    )
    if nm:
        for m in re.finditer(r"\\notetext\{(\d+)\}\{([^}]*)\}", nm.group(1)):
            annotations.append({"num": m.group(1), "text": m.group(2).strip()})

    return {
        "meta": meta,
        "poem": poem,
        "appreciation": appreciation,
        "annotations": annotations,
        "path": filepath,
        "dynasty_dir": filepath.parent.name,
        "slug": filepath.stem,
    }


def scan_poems() -> dict[str, list[dict]]:
    """扫描 content/poems/ 下所有 .tex 文件，按朝代分组。"""
    poems_by_dynasty: dict[str, list[dict]] = {}
    poems_dir = CONTENT_DIR / "poems"

    for dynasty_name, dynasty_dir in DYNASTIES:
        d = poems_dir / dynasty_dir
        if not d.is_dir():
            continue
        poems = []
        for f in sorted(d.glob("*.tex")):
            if f.name.startswith("_"):  # 跳过 _intro.tex 等辅助文件
                continue
            data = parse_tex(f)
            if data:
                poems.append(data)
        poems.sort(key=lambda p: int(p["meta"].get("order", 0)))
        poems_by_dynasty[dynasty_name] = poems

    return poems_by_dynasty


# ── 书构建 ─────────────────────────────────────────
def build_book(poems_by_dynasty: dict[str, list[dict]]) -> None:
    """在 main.tex 骨架中插入章节和 \input 语句，然后编译 PDF。"""
    main_tex = BOOK_DIR / "main.tex"
    if not main_tex.exists():
        print("Error: book/main.tex not found")
        return

    skeleton = main_tex.read_text(encoding="utf-8")

    # 生成章节内容
    lines = []
    poems_dir = CONTENT_DIR / "poems"
    for dynasty_name, dynasty_dir in DYNASTIES:
        poems = poems_by_dynasty.get(dynasty_name, [])
        if not poems:
            continue
        lines.append(f"\\chapter{{{dynasty_name}}}")

        # 朝代导言（可选，之后分页）
        intro_file = poems_dir / dynasty_dir / "_intro.tex"
        if intro_file.exists():
            intro_rel = os.path.relpath(intro_file, BOOK_DIR).replace("\\", "/")
            lines.append(f"\\input{{{intro_rel}}}")
            lines.append("\\newpage")

        for p in poems:
            rel = os.path.relpath(p["path"], BOOK_DIR).replace("\\", "/")
            title = p["meta"]["title"]
            author = p["meta"]["author"]
            lines.append(f"\\poemheading{{{title}}}{{{author}}}{{{dynasty_name}}}")
            lines.append(f"\\input{{{rel}}}")
            lines.append("\\newpage")
            lines.append("")

    chapter_text = "\n".join(lines)

    # 替换骨架中的 GENERATED 标记区间
    begin_marker = "%% GENERATED_CHAPTERS_BEGIN"
    end_marker = "%% GENERATED_CHAPTERS_END"
    begin_idx = skeleton.find(begin_marker)
    end_idx = skeleton.find(end_marker)
    if begin_idx == -1 or end_idx == -1:
        print("Error: GENERATED markers not found in main.tex")
        return
    before = skeleton[: begin_idx + len(begin_marker)]
    after = skeleton[end_idx:]
    generated = before + "\n" + chapter_text + "\n" + after

    # 写入临时文件
    tmp = BOOK_DIR / "main_generated.tex"
    tmp.write_text(generated, encoding="utf-8")

    # 编译
    cwd = os.getcwd()
    os.chdir(BOOK_DIR)
    try:
        subprocess.run(
            ["latexmk", "-xelatex", "-interaction=nonstopmode", "main_generated.tex"],
            check=False,
        )
    finally:
        os.chdir(cwd)

    # 复制 PDF 到 output/
    pdf_src = BOOK_DIR / "main_generated.pdf"
    if pdf_src.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(pdf_src), str(OUTPUT_DIR / "book.pdf"))
        print("Book built -> output/book.pdf")
    else:
        print("Error: PDF compilation failed — check LaTeX log for details")


# ── 文本清理 ───────────────────────────────────────
def clean_latex(text: str) -> str:
    """移除基本 LaTeX 命令，返回纯文本。"""
    text = re.sub(r"\\\w+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\(?!\n)", "", text)
    return text.strip()


def clean_poem_text(text: str) -> str:
    """清理诗歌文本，将 \textsuperscript{N} 转为 <sup>N</sup>，移除其余 LaTeX 命令。"""
    text = re.sub(r"\\textsuperscript\{(\d+)\}", r"<sup>\1</sup>", text)
    text = re.sub(r"\\\w+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\(?!\n)", "", text)
    return text.strip()


# ── 网站构建 ───────────────────────────────────────
def build_site(poems_by_dynasty: dict[str, list[dict]]) -> None:
    """从 .tex 提取内容，通过 Jinja2 生成静态网站。"""
    env = Environment(
        loader=FileSystemLoader(SITE_DIR / "templates"),
        autoescape=True,
    )

    # 清理输出
    if SITE_OUTPUT.exists():
        shutil.rmtree(SITE_OUTPUT)
    SITE_OUTPUT.mkdir(parents=True)

    # 复制静态资源
    static_src = SITE_DIR / "static"
    if static_src.exists():
        shutil.copytree(static_src, SITE_OUTPUT / "static")

    # 朝代导言
    dynasty_intros = {}
    dynasty_summaries = {}
    for dynasty_name, dynasty_dir in DYNASTIES:
        intro_file = CONTENT_DIR / "poems" / dynasty_dir / "_intro.tex"
        if intro_file.exists():
            text = intro_file.read_text(encoding="utf-8")
            sm = re.search(r"^%\s*!SUMMARY\s+(.+)$", text, re.MULTILINE)
            if sm:
                dynasty_summaries[dynasty_name] = sm.group(1).strip()
            m = re.search(
                r"\\begin\{intro\}\s*\n(.*?)\n\s*\\end\{intro\}",
                text,
                re.DOTALL,
            )
            if m:
                dynasty_intros[dynasty_name] = clean_latex(m.group(1).strip())

    # 构建诗歌数据结构
    all_poems = []
    for dynasty_name, dynasty_dir in DYNASTIES:
        poems = poems_by_dynasty.get(dynasty_name, [])
        for p in poems:
            p["dynasty"] = dynasty_name
            p["dynasty_dir"] = dynasty_dir
            p["poem_clean"] = clean_poem_text(p["poem"])
            p["appreciation_clean"] = clean_latex(p["appreciation"])
            all_poems.append(p)

    # 首页
    idx_tpl = env.get_template("index.html")
    dynasty_order = [d for d, _ in DYNASTIES if poems_by_dynasty.get(d)]
    idx_html = idx_tpl.render(
        poems_by_dynasty=poems_by_dynasty,
        dynasty_order=dynasty_order,
        dynasty_intros=dynasty_intros,
        dynasty_summaries=dynasty_summaries,
        base_url=BASE_URL,
    )
    (SITE_OUTPUT / "index.html").write_text(idx_html, encoding="utf-8")

    # 朝代目录页
    intro_tpl = env.get_template("intro.html")
    for dynasty_name, dynasty_dir in DYNASTIES:
        poems = poems_by_dynasty.get(dynasty_name, [])
        if not poems:
            continue
        html = intro_tpl.render(
            dynasty=dynasty_name,
            dynasty_summary=dynasty_summaries.get(dynasty_name, ""),
            intro_text=dynasty_intros.get(dynasty_name, ""),
            poems=poems,
            base_url=BASE_URL,
        )
        out = SITE_OUTPUT / dynasty_dir / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

    # 每首诗独立页面
    poem_tpl = env.get_template("poem.html")
    for i, p in enumerate(all_poems):
        next_poem = None
        if i + 1 < len(all_poems):
            nxt = all_poems[i + 1]
            next_poem = {
                "title": nxt["meta"]["title"],
                "url": f"{nxt['dynasty_dir']}/{nxt['slug']}.html",
            }
        html = poem_tpl.render(poem=p, next_poem=next_poem, base_url=BASE_URL)
        out = SITE_OUTPUT / p["dynasty_dir"] / f"{p['slug']}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

    # 关于页
    about_tpl = env.get_template("about.html")
    about_html = about_tpl.render(base_url=BASE_URL)
    (SITE_OUTPUT / "about.html").write_text(about_html, encoding="utf-8")

    print(f"Site built -> {SITE_OUTPUT}")


# ── 主入口 ─────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Gift build script")
    parser.add_argument("--book", action="store_true", help="仅构建 PDF")
    parser.add_argument("--site", action="store_true", help="仅构建网站")
    args = parser.parse_args()

    do_book = args.book or (not args.site)
    do_site = args.site or (not args.book)

    poems = scan_poems()
    if not poems:
        print("No poems found in content/poems/")
        return

    if do_book:
        build_book(poems)
    if do_site:
        build_site(poems)


if __name__ == "__main__":
    main()
