# Gift — 给妹妹的中国古代诗歌赏析书

## 项目目标

- 一本书：LaTeX 排版的中国古代诗歌赏析集，面向青少年读者
- 一个站：静态网站展示同样内容，方便在线阅读
- 单一数据源：诗歌原文和赏析文字只用 LaTeX（.tex）编写，网站内容从 .tex 提取

## 技术栈

- **内容源**：.tex 文件（LaTeX 正文 + 注释行元信息），UTF-8 编码
- **书**：XeLaTeX + ctexbook 文档类 → PDF
- **站**：Python 3 + Jinja2 生成静态 HTML，纯 CSS
- **构建**：Python 脚本 —— 扫描 content/ 生成 main.tex 并编译 PDF；解析 .tex 提取内容生成网站
- **环境**：conda 隔离环境，依赖写入 environment.yml

## 目录结构

```
/
├── content/                # 单一数据源：诗歌 .tex 文件
│   ├── preface.tex         # 前言/自序（可选）
│   └── poems/              # 按朝代分组：先秦→两汉→魏晋→南北朝→唐→两宋→元→明清→近代
│       ├── xian-qin/
│       ├── liang-han/
│       ├── wei-jin/
│       ├── nan-bei-chao/
│       ├── tang/
│       ├── liang-song/
│       ├── yuan/
│       ├── ming-qing/
│       └── jin-dai/
├── book/                   # LaTeX 书稿
│   ├── main.tex            # 主文件骨架（build.py 根据 content/ 自动生成，但手动维护 \documentclass 和 preamble 引用）
│   ├── preamble.tex        # 宏包加载和自定义环境（\poem、\appreciation 宏定义）
│   └── assets/             # 插图、题图等图片资源
├── site/                   # 静态网站
│   ├── templates/          # Jinja2 模板
│   │   ├── base.html
│   │   ├── index.html
│   │   └── poem.html
│   ├── static/             # CSS
│   │   └── style.css
│   └── output/             # 网站构建输出（gitignore）
├── scripts/
│   └── build.py            # 统一构建脚本
├── output/                 # PDF 输出（gitignore）
├── environment.yml
├── .gitignore
└── CLAUDE.md
```

## 内容格式约定

### .tex 内容文件模板

每首诗一个 .tex 文件，只包含元信息注释和两个环境，不包含 \documentclass 等头部：

```latex
% !TITLE 静夜思
% !AUTHOR 李白
% !DYNASTY 唐
% !GENRE 五言绝句
% !ORDER 1

\begin{poem}
床前明月光，疑是地上霜。
举头望明月，低头思故乡。
\end{poem}

\begin{annotations}
\notetext{1}{疑：怀疑、恍惚以为是。……}
\end{annotations}

\begin{appreciation}
赏析文字……
\end{appreciation}
```

- 文件名：拼音-连字符，如 `jing-ye-si.md` → `jing-ye-si.tex`
- 注释行的元信息必须包含：`!TITLE`、`!AUTHOR`、`!DYNASTY`、`!ORDER`。`!GENRE` 可选
- `!DYNASTY` 必须是以下九个值之一：先秦、两汉、魏晋、南北朝、唐、两宋、元、明清、近代
- `!ORDER` 为整数，决定同一朝代内部排序
- `\begin{poem}...\end{poem}` 包含诗歌原文，`\begin{annotations}...\end{annotations}` 包含注释
- `\begin{appreciation}...\end{appreciation}` 包含赏析（可选，由用户自行撰写）
- Claude 新增诗歌时，只需写诗歌正文和注释，**不要写赏析**——赏析由用户自己完成
- 文件尾部不写空行或多余标记

### 书的拼装

**book/main.tex** 是手动维护的骨架，固定头部如下：

```latex
\documentclass[UTF8]{ctexbook}
\input{preamble}

\begin{document}

\title{中国古代诗歌赏析}
\author{陈顶立}
\maketitle
\tableofcontents

%% GENERATED_CHAPTERS_BEGIN
% build.py 在此之间自动插入 \chapter{} 和 \input{} 语句
%% GENERATED_CHAPTERS_END

\end{document}
```

build.py 扫描 content/poems/ 下各朝代目录，按 ORDER 排序，在 `GENERATED` 标记之间自动生成：

```latex
\chapter{唐代诗歌}
\input{../content/poems/tang/jing-ye-si.tex}
\input{../content/poems/tang/chun-xiao.tex}

\chapter{宋代诗歌}
\input{../content/poems/liang-song/...}
```

你只需维护 preamble.tex 和 main.tex 的骨架头部，build.py 负责拼装章节列表。

### 网站生成

build.py 解析 .tex 文件时，用正则提取注释行元信息和 `\poem{}`、`\appreciation{}` 的大括号内容，转为 Python 数据结构，再通过 Jinja2 渲染为 HTML。

解析规则：

- `^% !(\w+)\s+(.+)$` 提取元信息
- `\\begin\{poem\}([\s\S]*?)\\end\{poem\}` 提取诗歌正文
- `\\begin\{appreciation\}([\s\S]*?)\\end\{appreciation\}` 提取赏析

提取后的文本为原始 LaTeX 字符串，需做基本清理（去掉 LaTeX 命令，只保留纯文本）再输出到 HTML。后续如有特殊排版需求，在解析器中增量添加清理规则即可。

## 构建流程

```bash
python scripts/build.py          # 全量：生成 main.tex + 编译 PDF + 生成网站
python scripts/build.py --book   # 仅书
python scripts/build.py --site   # 仅网站
```

### build.py 职责

1. 扫描 content/poems/ 下所有 .tex 文件，解析元信息
2. 按朝代 → ORDER 排序，将 `\chapter{}` 和 `\input{}` 插入 main.tex 的 GENERATED 标记区间
3. 调用 latexmk -xelatex 编译 PDF，输出到 output/book.pdf
4. 从 .tex 提取纯文本，通过 Jinja2 生成 HTML 到 site/output/

## LaTeX 约定

- 引擎：XeLaTeX（通过 latexmk 调用，配置文件 latexmkrc）
- 中文：ctexbook 文档类
- 自定义环境：在 preamble.tex 中定义 `\poem` 和 `\appreciation` 宏，控制诗歌和赏析的字体、行距、边距等
- 字体：中文字体使用系统自带（思源宋体或 Windows 宋体/楷体）
- 图片：统一放 book/assets/，用相对路径引用

## 网站约定

- 静态 HTML，无 JS
- 响应式布局，适配手机阅读
- 导航：首页（朝代目录）→ 朝代诗单 → 单首赏析
- 每首诗独立页面，支持直接分享 URL
- 字体优先系统自带中文字体

## 开发纪律

- 先写好 2-3 篇示例 .tex 内容，再搭构建脚本
- **内容文件和构建逻辑分离**：改赏析改 .tex 文件，改排版改 preamble.tex，改样式改 CSS，互不污染
- main.tex 主体手动维护但章节部分由 build.py 自动生成，不要手动编辑 GENERATED 标记之间的内容
- 每次改动构建脚本后跑完整构建验证
- output/ 和 site/output/ 不进 git
- `\poem{}` 和 `\appreciation{}` 内部尽量保持纯文本，复杂排版通过 preamble.tex 中的宏定义实现，不写在内容文件里

## 设计原则

- 单篇赏析 300-600 字，语言通俗但有深度，适合小学生阅读
- 每首诗配简短背景介绍（诗人、创作背景），不默认读者知道
- 赏析重点：意象分析、情感表达、语言妙处，避免学术术语堆砌
