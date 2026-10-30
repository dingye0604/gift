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

# 分卷《先秦·两汉·魏晋篇》只收前三章，与全书共用 content/ 和 preamble.tex
VOLUME_DYNASTIES = ("先秦", "两汉", "魏晋")
VOLUME_SKELETON = "main_volume.tex"
VOLUME_GENERATED = "main_volume_generated.tex"
VOLUME_OUTPUT = "book-volume.pdf"

# 河流渡口 Y 位置（与 CSS .river-port--N 的 --y 值对应，0-1 比例）
RIVER_PORT_Y = [0.085, 0.175, 0.265, 0.355, 0.455, 0.545, 0.635, 0.725, 0.815, 0.900]
# 河流渡口 X 中心位置（从 SVG path 估算）
RIVER_PORT_X = [445, 462, 438, 535, 560, 478, 462, 510, 598, 690]
RIVER_HEIGHT = 2100
RIVER_WIDTH = 960


def get_river_viewbox(port_index: int, zoom: str) -> str:
    """根据朝代渡口位置计算 sidebar SVG 的 viewBox。

    port_index: 0-based，对应 RIVER_PORT_Y 中的索引
    zoom: 'dynasty'（约 23% 高度）或 'poem'（约 11% 高度）
    """
    center_y = RIVER_PORT_Y[port_index] * RIVER_HEIGHT
    center_x = RIVER_PORT_X[port_index]
    
    if zoom == "dynasty":
        vb_w = 480
        vb_h = 480
    else:  # poem
        vb_w = 280
        vb_h = 230
        
    vb_x = max(0, min(center_x - vb_w / 2, RIVER_WIDTH - vb_w))
    vb_y = max(0, min(center_y - vb_h / 2, RIVER_HEIGHT - vb_h))
    return f"{vb_x:.0f} {vb_y:.0f} {vb_w:.0f} {vb_h:.0f}"


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
        "sources": source_details(meta),
        "poem": poem,
        "appreciation": appreciation,
        "annotations": annotations,
        "path": filepath,
        "dynasty_dir": filepath.parent.name,
        "slug": filepath.stem,
    }


def source_details(meta: dict) -> list[dict[str, str]]:
    """返回篇末显示的底本信息；!SOURCE 仅作内部记录，不显示。"""
    details = []
    if meta.get("edition"):
        status = meta.get("edition_status", "pending")
        if status not in {"pending", "verified"}:
            raise ValueError(f"Invalid edition status: {status}")
        label = "采用底本" if status == "verified" else "底本"
        details.append({"label": label, "text": meta["edition"]})
        if meta.get("locator"):
            details.append({"label": "底本定位", "text": meta["locator"]})
    return details


def scan_poems() -> dict[str, list[dict]]:
    """保留历史文件路径，按真实朝代元信息分章。"""
    poems_by_dynasty: dict[str, list[dict]] = {name: [] for name, _ in DYNASTIES}
    dynasty_dirs = dict(DYNASTIES)
    poems_dir = CONTENT_DIR / "poems"

    for dynasty_name, dynasty_dir in DYNASTIES:
        d = poems_dir / dynasty_dir
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.tex")):
            if f.name.startswith("_"):  # 跳过 _intro.tex 等辅助文件
                continue
            data = parse_tex(f)
            if data:
                actual_dynasty = data["meta"].get("dynasty", dynasty_name)
                if actual_dynasty not in dynasty_dirs:
                    raise ValueError(f"Unknown dynasty in {f}: {actual_dynasty}")
                data["dynasty_dir"] = dynasty_dirs[actual_dynasty]
                poems_by_dynasty[actual_dynasty].append(data)
    for poems in poems_by_dynasty.values():
        poems.sort(key=lambda p: int(p["meta"].get("order", 0)))

    return poems_by_dynasty


# ── 书构建 ─────────────────────────────────────────
def build_book(
    poems_by_dynasty: dict[str, list[dict]],
    *,
    skeleton_name: str = "main.tex",
    generated_name: str = "main_generated.tex",
    output_name: str = "book.pdf",
    dynasties: tuple[str, ...] | None = None,
) -> None:
    r"""在骨架中插入章节和 \input 语句，然后编译 PDF。

    默认构建全书；传入 dynasties 可只收指定朝代（用于分卷）。
    """
    main_tex = BOOK_DIR / skeleton_name
    if not main_tex.exists():
        print(f"Error: book/{skeleton_name} not found")
        return

    skeleton = main_tex.read_text(encoding="utf-8")

    # 生成章节内容
    lines = []
    poems_dir = CONTENT_DIR / "poems"
    for dynasty_name, dynasty_dir in DYNASTIES:
        if dynasties is not None and dynasty_name not in dynasties:
            continue
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
            if p["sources"]:
                lines.append("\\begin{poemsources}")
            for source in p["sources"]:
                lines.append(
                    f"\\poemsource{{{escape_latex(source['label'])}}}"
                    f"{{{escape_latex(source['text'])}}}"
                )
            if p["sources"]:
                lines.append("\\end{poemsources}")
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
    tmp = BOOK_DIR / generated_name
    tmp.write_text(generated, encoding="utf-8")

    # 编译
    cwd = os.getcwd()
    os.chdir(BOOK_DIR)
    try:
        subprocess.run(
            ["latexmk", "-xelatex", "-interaction=nonstopmode", generated_name],
            check=True,
        )
    finally:
        os.chdir(cwd)

    # 复制 PDF 到 output/
    pdf_src = BOOK_DIR / Path(generated_name).with_suffix(".pdf").name
    if pdf_src.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(pdf_src), str(OUTPUT_DIR / output_name))
        print(f"Book built -> {OUTPUT_DIR / output_name}")
    else:
        raise FileNotFoundError(f"PDF compilation produced no {pdf_src.name}")


def escape_latex(text: str) -> str:
    """来源字段是纯文本，不能把出版社/书名中的符号当作TeX执行。"""
    replacements = {
        "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
        "%": r"\%", "&": r"\&", "_": r"\_", "#": r"\#",
        "$": r"\$", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


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
def build_site(poems_by_dynasty: dict[str, list[dict]], *, clean_output: bool = True) -> None:
    """从 .tex 提取内容，通过 Jinja2 生成静态网站。"""
    env = Environment(
        loader=FileSystemLoader(SITE_DIR / "templates"),
        autoescape=True,
    )

    # 清理输出（先清内容，删不掉目录就留着，Windows 有时会锁目录）
    if clean_output and SITE_OUTPUT.exists():
        for item in list(SITE_OUTPUT.iterdir()):
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    SITE_OUTPUT.mkdir(parents=True, exist_ok=True)

    # 复制静态资源
    static_src = SITE_DIR / "static"
    if static_src.exists():
        shutil.copytree(static_src, SITE_OUTPUT / "static", dirs_exist_ok=not clean_output)

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
        port_idx = dynasty_order.index(dynasty_name)
        river_viewbox = get_river_viewbox(port_idx, "dynasty")
        html = intro_tpl.render(
            dynasty=dynasty_name,
            dynasty_summary=dynasty_summaries.get(dynasty_name, ""),
            intro_text=dynasty_intros.get(dynasty_name, ""),
            poems=poems,
            river_viewbox=river_viewbox,
            river_zoom_class="river-zoom-dynasty",
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
        port_idx = dynasty_order.index(p["dynasty"])
        river_viewbox = get_river_viewbox(port_idx, "poem")
        html = poem_tpl.render(
            poem=p,
            dynasty_summary=dynasty_summaries.get(p["dynasty"], ""),
            next_poem=next_poem,
            river_viewbox=river_viewbox,
            river_zoom_class="river-zoom-poem",
            base_url=BASE_URL,
        )
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
    global OUTPUT_DIR, SITE_OUTPUT
    parser = argparse.ArgumentParser(description="Gift build script")
    parser.add_argument("--book", action="store_true", help="仅构建全书 PDF")
    parser.add_argument("--site", action="store_true", help="仅构建网站")
    parser.add_argument(
        "--volume",
        action="store_true",
        help="仅构建分卷《先秦·两汉·魏晋篇》PDF",
    )
    parser.add_argument("--output-root", type=Path, help="独立校订输出目录，内含book.pdf和site/")
    args = parser.parse_args()
    if args.volume and args.site:
        parser.error("--volume 只构建分卷 PDF，不能与 --site 同时使用")
    if args.output_root:
        OUTPUT_DIR = args.output_root.resolve()
        SITE_OUTPUT = OUTPUT_DIR / "site"

    if args.volume:
        do_book, do_site = True, False
    else:
        do_book = args.book or (not args.site)
        do_site = args.site or (not args.book)

    poems = scan_poems()
    if not poems:
        print("No poems found in content/poems/")
        return

    if do_book:
        if args.volume:
            build_book(
                poems,
                skeleton_name=VOLUME_SKELETON,
                generated_name=VOLUME_GENERATED,
                output_name=VOLUME_OUTPUT,
                dynasties=VOLUME_DYNASTIES,
            )
        else:
            build_book(poems)
    if do_site:
        build_site(poems, clean_output=not args.output_root)


if __name__ == "__main__":
    main()
