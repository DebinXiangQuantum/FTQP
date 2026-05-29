from __future__ import annotations

import os
import re
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from PIL import Image


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "popl_survey.pptx"
OUTPUT = ROOT / "popl_quantum_ftqc_survey.pptx"
ASSETS = ROOT / "popl_survey_assets" / "figures"

EMU_PER_IN = 914400
SLIDE_W = 12192000
SLIDE_H = 6858000

NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

ET.register_namespace("", NS_CT)
ET.register_namespace("p", NS_P)
ET.register_namespace("r", NS_R)


def emu(v: float) -> int:
    return int(v * EMU_PER_IN)


def rgb(color: str) -> str:
    return color.strip("#").upper()


def xesc(text: str) -> str:
    return escape(text, {'"': "&quot;"})


def shape_id_gen():
    i = 2
    while True:
        yield i
        i += 1


def tx_font(size: int, color: str = "#1F2933", bold: bool = False) -> str:
    b = ' b="1"' if bold else ""
    return (
        f'<a:rPr lang="zh-CN" altLang="en-US" sz="{size * 100}"{b} kern="1200">'
        f'<a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill>'
        '<a:latin typeface="微软雅黑"/><a:ea typeface="微软雅黑"/><a:cs typeface="微软雅黑"/>'
        "</a:rPr>"
    )


def para_xml(text: str, size: int = 18, color: str = "#1F2933", bold: bool = False, align: str = "l") -> str:
    ppr = f'<a:pPr algn="{align}"><a:lnSpc><a:spcPct val="108000"/></a:lnSpc></a:pPr>'
    return f"<a:p>{ppr}<a:r>{tx_font(size, color, bold)}<a:t>{xesc(text)}</a:t></a:r></a:p>"


def text_box(
    sid: int,
    x: float,
    y: float,
    w: float,
    h: float,
    paragraphs: list[str] | str,
    size: int = 18,
    color: str = "#1F2933",
    bold: bool = False,
    align: str = "l",
    name: str = "Text",
) -> str:
    if isinstance(paragraphs, str):
        paragraphs = paragraphs.split("\n")
    body = "".join(para_xml(p, size=size, color=color, bold=bold, align=align) for p in paragraphs)
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{sid}" name="{xesc(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
      <p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
      <p:txBody><a:bodyPr wrap="square" lIns="18000" rIns="18000" tIns="9000" bIns="9000"/><a:lstStyle/>{body}</p:txBody>
    </p:sp>
    """


def rect_shape(
    sid: int,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str = "#F3F6FA",
    line: str = "#D7DEE8",
    radius: str = "roundRect",
    name: str = "Shape",
) -> str:
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{sid}" name="{xesc(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
        <a:prstGeom prst="{radius}"><a:avLst/></a:prstGeom>
        <a:solidFill><a:srgbClr val="{rgb(fill)}"/></a:solidFill>
        <a:ln w="9525"><a:solidFill><a:srgbClr val="{rgb(line)}"/></a:solidFill></a:ln>
      </p:spPr>
    </p:sp>
    """


def line_shape(sid: int, x1: float, y1: float, x2: float, y2: float, color: str = "#4472C4", width: int = 2) -> str:
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    flip_h = ' flipH="1"' if x2 < x1 else ""
    flip_v = ' flipV="1"' if y2 < y1 else ""
    return f"""
    <p:cxnSp>
      <p:nvCxnSpPr><p:cNvPr id="{sid}" name="Line"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
      <p:spPr><a:xfrm{flip_h}{flip_v}><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
        <a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>
        <a:ln w="{width * 12700}"><a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill></a:ln>
      </p:spPr>
    </p:cxnSp>
    """


def image_shape(sid: int, rid: str, x: float, y: float, w: float, h: float, name: str = "Picture") -> str:
    return f"""
    <p:pic>
      <p:nvPicPr><p:cNvPr id="{sid}" name="{xesc(name)}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>
      <p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
      <p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
    </p:pic>
    """


def fit_image(path: Path, x: float, y: float, max_w: float, max_h: float) -> tuple[float, float, float, float]:
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    w = iw * scale
    h = ih * scale
    return x + (max_w - w) / 2, y + (max_h - h) / 2, w, h


def slide_number(sid: int, n: int) -> str:
    return text_box(sid, 12.57, 0.06, 0.43, 0.34, str(n), size=12, color="#FFFFFF", bold=True, align="ctr", name="Slide Number")


def title(sid: int, text: str) -> str:
    return text_box(sid, 0.55, 0.28, 11.0, 0.55, text, size=30, color="#111827", bold=True, name="Title")


def footer(sid: int, cite: str) -> str:
    return text_box(sid, 6.65, 7.14, 5.95, 0.24, cite, size=10, color="#4B5563", align="r", name="Citation")


def bullet_block(sid_iter, x: float, y: float, w: float, lines: list[str], color: str = "#1F2933") -> str:
    lines = [line.replace("• ", "", 1) for line in lines]
    return text_box(next(sid_iter), x, y, w, 0.42 * len(lines) + 0.2, lines, size=18, color=color, name="Bullets")


def fig_title(sid_iter, text: str, x: float, y: float, w: float) -> str:
    return text_box(next(sid_iter), x, y, w, 0.52, text, size=16, color="#111827", bold=True, align="ctr", name="Figure title")


def add_image(slide_parts: list[str], rels: list[tuple[str, str]], sid_iter, filename: str, x: float, y: float, w: float, h: float, title_text: str | None = None) -> None:
    img = ASSETS / filename
    rid = f"rId{len(rels) + 2}"
    rels.append((rid, f"../media/{filename}"))
    if title_text:
        slide_parts.append(fig_title(sid_iter, title_text, x, y - 0.60, w))
    ix, iy, iw, ih = fit_image(img, x, y, w, h)
    slide_parts.append(image_shape(next(sid_iter), rid, ix, iy, iw, ih, name=filename))


def make_slide(n: int, spec: dict) -> tuple[str, str]:
    sid_iter = shape_id_gen()
    rels: list[tuple[str, str]] = [("rId1", "../slideLayouts/slideLayout1.xml")]
    parts: list[str] = []
    parts.append(slide_number(next(sid_iter), n))
    parts.append(title(next(sid_iter), spec["title"]))
    for item in spec.get("items", []):
        kind = item["type"]
        if kind == "text":
            parts.append(text_box(next(sid_iter), *item["box"], item["text"], size=item.get("size", 18), color=item.get("color", "#1F2933"), bold=item.get("bold", False), align=item.get("align", "l"), name=item.get("name", "Text")))
        elif kind == "bullets":
            parts.append(bullet_block(sid_iter, *item["box"], item["lines"], color=item.get("color", "#1F2933")))
        elif kind == "rect":
            parts.append(rect_shape(next(sid_iter), *item["box"], fill=item.get("fill", "#F3F6FA"), line=item.get("line", "#D7DEE8"), name=item.get("name", "Shape")))
        elif kind == "line":
            parts.append(line_shape(next(sid_iter), *item["coords"], color=item.get("color", "#4472C4"), width=item.get("width", 2)))
        elif kind == "image":
            add_image(parts, rels, sid_iter, item["file"], *item["box"], title_text=item.get("title"))
    parts.append(footer(next(sid_iter), spec.get("cite", "")))
    body = "".join(parts)
    slide_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
    {body}
  </p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''
    rel_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    for rid, target in rels:
        typ = "slideLayout" if target.endswith("slideLayout1.xml") else "image"
        rel_xml += f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{typ}" Target="{xesc(target)}"/>'
    rel_xml += "</Relationships>"
    return slide_xml, rel_xml


SLIDES: list[dict] = [
    {
        "title": "POPL 量子程序语言论文调研",
        "items": [
            {"type": "text", "box": (0.75, 1.32, 10.8, 0.85), "text": "从 Zotero `reference/POPL` 的 29 篇论文出发，归纳量子 PL 的主题谱系，并落到 universal FTQC 的 POPL 2027 选题。", "size": 22, "color": "#1F2933"},
            {"type": "line", "coords": (0.75, 2.42, 11.5, 2.42), "color": "#4472C4", "width": 3},
            {"type": "bullets", "box": (0.86, 2.82, 11.0), "lines": [
                "• 讲解主线：语言抽象、类型/资源、逻辑、自动验证、编译优化。",
                "• 翻译原则：中文讲解保持术语严谨，关键新名词保留英文解释。",
                "• FTQC 结论：code switching 与 magic resources 应成为 typed/effectful IR 的一等对象。",
            ]},
        ],
        "cite": "Sources: Zotero reference/POPL collection; POPL_quantum_FTQC_survey.md",
    },
    {
        "title": "总体判断：POPL 关注“可组合的软件抽象”",
        "items": [
            {"type": "bullets", "box": (0.78, 1.18, 11.3), "lines": [
                "• 成功论文通常不是直接发明量子协议，而是把低层对象重塑成可编程、可推理、可优化的抽象。",
                "• 形式核心要小而硬：language、type/effect system、logic、semantics、automata、IR 或 DSL。",
                "• 正确性叙事要明确：soundness、completeness、full abstraction、type safety、resource bound soundness。",
                "• 证据不能停在玩具例子：实现、case studies、benchmark、机械化证明或真实后端。",
            ]},
            {"type": "rect", "box": (1.0, 4.55, 10.9, 1.0), "fill": "#EEF5FF", "line": "#A7C3E8"},
            {"type": "text", "box": (1.2, 4.72, 10.5, 0.65), "text": "FTQC 的 POPL 入口：把 code、logical resource、postselection、decoder/feedforward、error budget 变成程序层面的类型和效果。", "size": 20, "bold": True, "color": "#183A5A", "align": "ctr"},
        ],
        "cite": "Survey synthesis from 29 Zotero POPL items, 2026-04-27",
    },
    {
        "title": "主题地图 A：语言抽象与语义基础",
        "items": [
            {"type": "text", "box": (0.78, 1.13, 11.4, 0.35), "text": "这些论文的共同点是：提升表达层次，同时给出可编译或可解释的数学语义。", "size": 18, "bold": True},
            {"type": "bullets", "box": (0.85, 1.8, 5.55), "lines": [
                "• Qunity: unified quantum/classical syntax",
                "• Quantum Circuits Are Just a Phase",
                "• Qudit Projective Cliffords / LambdaPC",
                "• SimuQ: Hamiltonian + AAIS interface",
                "• Pi / Square Roots / Hadamard-Pi",
            ]},
            {"type": "bullets", "box": (6.35, 1.8, 5.65), "lines": [
                "• Proto-Quipper with dynamic lifting",
                "• Semantics for variational quantum programming",
                "• Full abstraction for quantum lambda-calculus",
                "• Enriched presheaf model of Quantum FPC",
                "• Compact closed categories and reversible types",
            ]},
        ],
        "cite": "Voichick et al. 2023; Peng et al. 2024; Heunen et al. 2026; Fang et al. 2026",
    },
    {
        "title": "主题地图 B：保证、自动化与编译优化",
        "items": [
            {"type": "bullets", "box": (0.78, 1.18, 3.85), "lines": [
                "• Indexed monads",
                "• Flexible resource estimation",
                "• Qurts affine lifetimes",
                "• Quantum information effects",
                "• Twist purity/entanglement",
            ]},
            {"type": "bullets", "box": (4.55, 1.18, 3.95), "lines": [
                "• RapunSL / QSL",
                "• Expressive assertion language",
                "• CoqQ",
                "• Relational proofs",
                "• Quantum bisimilarity",
            ]},
            {"type": "bullets", "box": (8.45, 1.18, 3.9), "lines": [
                "• Dirac rewriting",
                "• LSTA / SWTA verification",
                "• QSynth",
                "• VOQC",
                "• QMR generation / relational analysis",
            ]},
            {"type": "text", "box": (1.0, 5.65, 11.0, 0.42), "text": "翻译口径：effect = 程序执行或电路生成携带的可静态追踪信息；capability = 后端可提供的受约束操作能力。", "size": 18, "color": "#374151"},
        ],
        "cite": "Hietala et al. 2021; Hirata & Heunen 2025; Abdulla et al. 2025/2026; Molavi et al. 2026",
    },
    {
        "title": "范式一：把后端能力变成语言/DSL 接口",
        "items": [
            {"type": "image", "file": "fig_simuq_framework.png", "box": (0.95, 1.52, 5.35, 1.3), "title": "图 1  SimuQ 的前端目标系统与后端 AAIS 能力接口"},
            {"type": "bullets", "box": (6.65, 1.45, 5.55), "lines": [
                "• Hamiltonian Modeling Language：用户描述目标系统。",
                "• AAIS Specification Language：硬件方声明 analog capability。",
                "• Solver-based compilation：把领域模型编译到 pulse schedule。",
                "• 对 FTQC 的类比：code/factory/decoder 也应有 capability specification。",
            ]},
            {"type": "text", "box": (0.95, 3.58, 11.1, 0.85), "text": "关键 insight：不要把硬件差异硬编码在 pass 里，而要把差异收敛到一个声明式接口。", "size": 22, "bold": True, "color": "#183A5A", "align": "ctr"},
        ],
        "cite": "Figure source: Peng et al., SimuQ, POPL 2024",
    },
    {
        "title": "范式一延伸：生成式编译器与 device state machine",
        "items": [
            {"type": "image", "file": "fig_amaro_overview.png", "box": (0.95, 1.48, 5.6, 1.15), "title": "图 2  Amaro: 由 QMR specification 生成 compiler"},
            {"type": "bullets", "box": (6.9, 1.4, 5.35), "lines": [
                "• QMR: logical circuit -> target QPU。",
                "• Device state machine: state/action/constraint/cost。",
                "• DSL 吸收后端差异；solver 保持可复用。",
                "• FTQC: surface code、atom arrays、lattice surgery 可共享抽象骨架。",
            ]},
            {"type": "image", "file": "fig_amaro_scmr.png", "box": (1.25, 3.58, 10.35, 2.62), "title": "图 3  Surface-code QMR: 并行路径与 T gate routing"},
        ],
        "cite": "Figure source: Molavi et al., Generating Compilers for QMR, POPL 2026",
    },
    {
        "title": "范式二：类型与 effect 管理量子资源",
        "items": [
            {"type": "image", "file": "fig_indexed_model.png", "box": (0.82, 1.38, 5.55, 3.65), "title": "图 4  Indexed monad 分离 value 与 circuit effect"},
            {"type": "bullets", "box": (6.7, 1.35, 5.45), "lines": [
                "• Indexed monad：用索引记录阶段和 effect 的变化。",
                "• Circuit algebra：抽象电路组合、优化与度量。",
                "• Resource analysis：类型推导给出 width、depth、gate count 等上界。",
                "• FTQC 类比：logical qubit count、code switch count、factory demand、decoder latency。",
            ]},
            {"type": "text", "box": (6.8, 4.9, 5.25, 0.68), "text": "英文解释：effect algebra 是把多种资源/误差指标按组合规则聚合的代数结构。", "size": 18, "color": "#374151"},
        ],
        "cite": "Figure source: Sakayori, Colledan & Dal Lago, POPL 2026",
    },
    {
        "title": "范式二案例：lifetime 让 uncomputation 成为资源纪律",
        "items": [
            {"type": "image", "file": "fig_qurts_pebble.png", "box": (0.82, 1.43, 6.25, 2.1), "title": "图 5  Qurts 用 pebbling 解释 time-space tradeoff"},
            {"type": "bullets", "box": (7.35, 1.38, 4.82), "lines": [
                "• Lifetime：借鉴 Rust 生命周期，限制 quantum value 的使用范围。",
                "• Affine within lifetime：生命周期内允许一定丢弃/复用。",
                "• Linear outside lifetime：边界处恢复线性使用，避免信息丢失。",
                "• FTQC 类比：magic states、ancilla patches、syndrome buffers 都有生命周期。",
            ]},
            {"type": "text", "box": (0.95, 4.5, 11.0, 0.72), "text": "把“资源是否还能被安全丢弃/重用”交给类型系统，比在后端脚本里手动维护状态更接近 POPL 的贡献点。", "size": 20, "bold": True, "color": "#183A5A", "align": "ctr"},
        ],
        "cite": "Figure source: Hirata & Heunen, Qurts, POPL 2025",
    },
    {
        "title": "范式三：逻辑恢复局部推理",
        "items": [
            {"type": "image", "file": "fig_rapunsl_rules.png", "box": (0.82, 1.48, 6.2, 1.25), "title": "图 6  RapunSL 的三类局部性规则"},
            {"type": "bullets", "box": (7.35, 1.35, 4.82), "lines": [
                "• Entanglement-locality：只证明被纠缠影响的局部区域。",
                "• Basis-locality：把 superposition reasoning 化约到 basis states。",
                "• Outcome-locality：把 measurement-induced mixed states 化约到 pure-state reasoning。",
                "• 新连接词：linear combination 与 mixing。",
            ]},
            {"type": "text", "box": (0.95, 4.05, 11.0, 0.75), "text": "对 FTQC：patch locality、syndrome locality、fault-propagation locality、factory locality 都可成为逻辑设计的切入点。", "size": 20, "bold": True, "color": "#183A5A", "align": "ctr"},
        ],
        "cite": "Figure source: Matsushita et al., RapunSL, POPL 2026",
    },
    {
        "title": "范式三延伸：断言语言与 foundational verification",
        "items": [
            {"type": "bullets", "box": (0.82, 1.22, 5.75), "lines": [
                "• Expressive assertion language：用 generalized Pauli operators 的 quasi-probability distributions 表示 quantum predicates。",
                "• CoqQ：在 Coq/MathComp 上建立 foundational soundness，断言可用 Dirac expressions。",
                "• Relational proofs：用 quantum couplings 验证等价、安全性与可靠性。",
            ]},
            {"type": "bullets", "box": (6.85, 1.22, 5.35), "lines": [
                "• FTQC assertion 应能表达：code membership、syndrome constraints、logical error budget。",
                "• weakest precondition closure 很关键：循环、feedforward、retry 才可组合证明。",
                "• 机械化证明可作为差异化证据，但不要让 proof engineering 淹没核心抽象。",
            ]},
            {"type": "line", "coords": (0.9, 5.15, 11.9, 5.15), "color": "#70AD47", "width": 3},
            {"type": "text", "box": (1.0, 5.38, 11.0, 0.55), "text": "英文解释：foundational verification 指逻辑 soundness 被连接到底层数学库，而不是只在论文中非形式化证明。", "size": 18, "color": "#374151", "align": "ctr"},
        ],
        "cite": "Su et al. 2026; Zhou et al. 2023; Barthe et al. 2019",
    },
    {
        "title": "范式四：有限符号表示支撑自动化验证",
        "items": [
            {"type": "image", "file": "fig_lsta.png", "box": (0.78, 1.36, 6.0, 2.55), "title": "图 7  LSTA 紧凑表示一族量子状态"},
            {"type": "bullets", "box": (7.08, 1.3, 5.05), "lines": [
                "• LSTA/SWTA：用同步树自动机表示指数或无限状态族。",
                "• Verification reduction：把电路正确性化约为 inclusion/equivalence checking。",
                "• Parameterized verification：验证任意输入规模生成的电路族。",
                "• FTQC 类比：code distance、syndrome rounds、factory level 都是参数。",
            ]},
        ],
        "cite": "Figure source: Abdulla et al., LSTA, POPL 2025; SWTA, POPL 2026",
    },
    {
        "title": "范式四案例：QSynth 把递归量子程序综合进 SMT",
        "items": [
            {"type": "image", "file": "fig_qsynth_overview.png", "box": (0.85, 1.38, 6.15, 2.25), "title": "图 8  QSynth workflow: specification, search, verification, backend export"},
            {"type": "bullets", "box": (7.3, 1.3, 4.88), "lines": [
                "• 目标不是合成一个固定 circuit，而是合成 recursive unitary programs。",
                "• Sound logic + SMT encoding 控制搜索空间。",
                "• 输出可转译到 Qiskit、Q#、Braket。",
                "• FTQC 机会：合成 code-switch schedule 或 factory protocol，需要 formal spec。",
            ]},
        ],
        "cite": "Figure source: Deng et al., QSynth, POPL 2024",
    },
    {
        "title": "范式五：量子优化可重述为经典静态分析",
        "items": [
            {"type": "image", "file": "fig_relational_phase.png", "box": (0.82, 1.38, 6.05, 1.85), "title": "图 9  Phase folding as affine relation analysis"},
            {"type": "bullets", "box": (7.18, 1.28, 5.0), "lines": [
                "• Phase folding 从 straight-line circuit 扩展到 loops 和 procedures。",
                "• Classical support：量子态中具有非零振幅的 classical basis states。",
                "• Affine/non-linear relational domains：借用经典抽象解释不变量。",
                "• FTQC 类比：code-switch minimization、factory scheduling、error-budget propagation。",
            ]},
            {"type": "image", "file": "fig_resource_teleport.png", "box": (1.45, 4.45, 4.6, 1.25), "title": "图 10  Resource metric: width / depth / gate count"},
            {"type": "text", "box": (6.55, 4.6, 5.35, 0.85), "text": "资源分析若只在后端统计，优化 pass 就很难证明不会突破预算；类型/效果系统把预算提前到程序层。", "size": 18, "color": "#374151"},
        ],
        "cite": "Figure sources: Amy & Lunderville, POPL 2025; Colledan & Dal Lago, POPL 2025",
    },
    {
        "title": "跨论文的 POPL 写法模板",
        "items": [
            {"type": "rect", "box": (0.88, 1.3, 2.6, 3.6), "fill": "#F8FAFC", "line": "#BFD2EA"},
            {"type": "rect", "box": (3.62, 1.3, 2.6, 3.6), "fill": "#F8FAFC", "line": "#BFD2EA"},
            {"type": "rect", "box": (6.36, 1.3, 2.6, 3.6), "fill": "#F8FAFC", "line": "#BFD2EA"},
            {"type": "rect", "box": (9.1, 1.3, 2.6, 3.6), "fill": "#F8FAFC", "line": "#BFD2EA"},
            {"type": "text", "box": (1.04, 1.55, 2.25, 2.8), "text": "1. 软件痛点\n\n后端碎片化、证明难、资源不可见、参数化电路不可验证。", "size": 18, "bold": True, "align": "ctr"},
            {"type": "text", "box": (3.78, 1.55, 2.25, 2.8), "text": "2. 小形式核心\n\n语言、类型、逻辑、自动机、IR、DSL 或语义模型。", "size": 18, "bold": True, "align": "ctr"},
            {"type": "text", "box": (6.52, 1.55, 2.25, 2.8), "text": "3. 明确定理\n\nsoundness、completeness、resource bound、optimizer correctness。", "size": 18, "bold": True, "align": "ctr"},
            {"type": "text", "box": (9.26, 1.55, 2.25, 2.8), "text": "4. 非玩具证据\n\nprototype、benchmark、case studies、机械化证明或真实后端。", "size": 18, "bold": True, "align": "ctr"},
            {"type": "line", "coords": (2.95, 3.1, 3.52, 3.1), "color": "#4472C4", "width": 3},
            {"type": "line", "coords": (5.7, 3.1, 6.25, 3.1), "color": "#4472C4", "width": 3},
            {"type": "line", "coords": (8.45, 3.1, 9.0, 3.1), "color": "#4472C4", "width": 3},
            {"type": "text", "box": (0.95, 5.42, 10.9, 0.45), "text": "FTQC 投稿应避免只做 protocol constants；主贡献要是可复用的软件抽象和证明。", "size": 20, "bold": True, "color": "#183A5A", "align": "ctr"},
        ],
        "cite": "Pattern distilled from POPL quantum PL papers, 2019-2026",
    },
    {
        "title": "FTQC 机会：后端协议正在变成可编程资源",
        "items": [
            {"type": "bullets", "box": (0.82, 1.2, 5.9), "lines": [
                "• Code switching：在不同 QECC codes 之间切换，获得不同 transversal gate capabilities。",
                "• Magic-state cultivation/distillation：生成 non-Clifford 资源态，具有 failure、latency、fidelity。",
                "• QLDPC / gauged logical measurement：高率 code 与 logical measurement 需要新能力接口。",
            ]},
            {"type": "bullets", "box": (6.88, 1.2, 5.35), "lines": [
                "• Decoder/feedforward：classical processing 影响阶段边界与时延。",
                "• Pauli frame：symbolic runtime state，记录待解释的 Pauli corrections。",
                "• Lattice surgery / patch routing：空间布局、并行性和 error budget 共同约束优化。",
            ]},
            {"type": "text", "box": (0.95, 5.38, 11.0, 0.62), "text": "核心变化：Universal FTQC 不再是单一 Clifford+T + distillation pipeline，而是多后端能力的组合。", "size": 20, "bold": True, "color": "#183A5A", "align": "ctr"},
        ],
        "cite": "Based on POPL/latest_FTQC_papers_and_POPL_topics.md, 2026-04-27",
    },
    {
        "title": "首选选题：Code-indexed probabilistic resource calculus",
        "items": [
            {"type": "text", "box": (0.82, 1.15, 11.25, 0.55), "text": "A Code-Indexed Probabilistic Resource Calculus for Universal Fault-Tolerant Quantum Programs", "size": 22, "bold": True, "color": "#183A5A", "align": "ctr"},
            {"type": "bullets", "box": (0.95, 2.05, 5.55), "lines": [
                "• `Q[code, distance, basis]`：encoded logical data 的类型。",
                "• `Switch c1 c2`：code switching 是 typestate transition。",
                "• `TState[epsilon]` / `CCZState[epsilon]`：线性概率资源。",
            ]},
            {"type": "bullets", "box": (6.78, 2.05, 5.3), "lines": [
                "• `Factory(rate, fail, latency)`：资源提供者。",
                "• `Decoder/feedforward`：带阶段和时延的 classical effect。",
                "• Effect algebra：聚合 qubit-rounds、error budget、switch count。",
            ]},
        ],
        "cite": "Concept synthesized from Qurts, Indexed Monads, QMR generation, RapunSL, and FTQC survey",
    },
    {
        "title": "核心 IR：types、capabilities、effects 三层分离",
        "items": [
            {"type": "rect", "box": (0.85, 1.35, 3.25, 3.4), "fill": "#EEF5FF", "line": "#7FA9D8"},
            {"type": "rect", "box": (4.95, 1.35, 3.25, 3.4), "fill": "#F1F8F1", "line": "#9BCB8B"},
            {"type": "rect", "box": (9.05, 1.35, 3.25, 3.4), "fill": "#FFF6E8", "line": "#F2B66D"},
            {"type": "text", "box": (1.05, 1.62, 2.85, 2.55), "text": "Type layer\n\nQ[code,d,basis]\nTState[ε]\nPatch[region]\nFrame[s]", "size": 18, "bold": True, "align": "ctr"},
            {"type": "text", "box": (5.15, 1.62, 2.85, 2.55), "text": "Capability library\n\nTransversal H\nLatticeSurgery CNOT\nSwitch A→B\nCultivate T", "size": 18, "bold": True, "align": "ctr"},
            {"type": "text", "box": (9.25, 1.62, 2.85, 2.55), "text": "Effect algebra\n\nlatency\nfailure prob.\nqubit-rounds\nlogical error", "size": 18, "bold": True, "align": "ctr"},
            {"type": "line", "coords": (4.18, 3.05, 4.85, 3.05), "color": "#4472C4", "width": 3},
            {"type": "line", "coords": (8.28, 3.05, 8.95, 3.05), "color": "#4472C4", "width": 3},
            {"type": "text", "box": (0.95, 5.35, 11.0, 0.55), "text": "分层原则：类型说“什么对象合法”，capability 说“后端能做什么”，effect 说“这样做的资源和风险是什么”。", "size": 20, "bold": True, "color": "#183A5A", "align": "ctr"},
        ],
        "cite": "Proposed IR structure for POPL 2027 FTQC topic",
    },
    {
        "title": "定理与评估：POPL 审稿人会看什么",
        "items": [
            {"type": "bullets", "box": (0.82, 1.2, 5.9), "lines": [
                "• Type preservation：code-indexed transitions 保持良构。",
                "• Logical soundness：擦除资源标注后仍实现目标 logical channel/unitary。",
                "• Fault-tolerance soundness：well-typed gadgets 满足指定 fault model。",
                "• Resource soundness：推导出的 resource/error bounds 是后端 cost model 上界。",
            ]},
            {"type": "bullets", "box": (6.88, 1.2, 5.35), "lines": [
                "• Optimization correctness：switch minimization、factory scheduling 不改变语义。",
                "• Prototype compiler：OpenQASM-like IR 或小型 logical circuit language。",
                "• 后端实例：surface code + color/Steane/code-switching + cultivation/factory。",
                "• Benchmarks：QFT、phase estimation、Hamiltonian kernels、T/CCZ-heavy arithmetic。",
            ]},
        ],
        "cite": "Evaluation plan synthesized from POPL quantum PL patterns and FTQC survey",
    },
    {
        "title": "结论：把 FTQC 从后端脚本提升为可验证 IR",
        "items": [
            {"type": "bullets", "box": (0.9, 1.28, 11.1), "lines": [
                "• POPL 的主贡献不是“更好的 distillation/cultivation protocol”，而是让协议族可组合、可检查、可优化。",
                "• 最稳路线：code-indexed types + probabilistic resource effects + verified compilation passes。",
                "• 最有传播力的写法：从一个 FTQC 软件痛点切入，用小形式核心给出定理，再用真实协议族做 case studies。",
                "• 不建议只做 resource spreadsheet；它可以是评估工具，但不能替代语言/类型/语义贡献。",
            ]},
            {"type": "text", "box": (1.0, 5.55, 10.95, 0.5), "text": "一句话：让 universal FTQC 的 code switching、magic resources 和 error accounting 成为程序语言对象。", "size": 22, "bold": True, "color": "#183A5A", "align": "ctr"},
        ],
        "cite": "Final synthesis based on Zotero POPL PDFs and local survey notes",
    },
]


def update_content_types(data: bytes, slide_count: int) -> bytes:
    root = ET.fromstring(data)
    for el in list(root):
        if el.tag == f"{{{NS_CT}}}Override" and el.attrib.get("PartName", "").startswith("/ppt/slides/slide"):
            root.remove(el)
    for i in range(1, slide_count + 1):
        ET.SubElement(root, f"{{{NS_CT}}}Override", {
            "PartName": f"/ppt/slides/slide{i}.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
        })
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_presentation(data: bytes, slide_count: int) -> bytes:
    root = ET.fromstring(data)
    sld_id_lst = root.find(f"{{{NS_P}}}sldIdLst")
    if sld_id_lst is None:
        raise RuntimeError("presentation.xml missing sldIdLst")
    for child in list(sld_id_lst):
        sld_id_lst.remove(child)
    for i in range(1, slide_count + 1):
        el = ET.SubElement(sld_id_lst, f"{{{NS_P}}}sldId", {"id": str(308 + i), f"{{{NS_R}}}id": f"rId{20 + i}"})
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_presentation_rels(data: bytes, slide_count: int) -> bytes:
    root = ET.fromstring(data)
    for el in list(root):
        if el.attrib.get("Type", "").endswith("/slide"):
            root.remove(el)
    for i in range(1, slide_count + 1):
        ET.SubElement(root, f"{{{NS_REL}}}Relationship", {
            "Id": f"rId{20 + i}",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
            "Target": f"slides/slide{i}.xml",
        })
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def update_app(data: bytes, slide_count: int) -> bytes:
    text = data.decode("utf-8")
    text = re.sub(r"<Slides>\d+</Slides>", f"<Slides>{slide_count}</Slides>", text)
    return text.encode("utf-8")


def build() -> None:
    slide_xmls: dict[str, bytes] = {}
    for i, spec in enumerate(SLIDES, 1):
        sxml, rxml = make_slide(i, spec)
        slide_xmls[f"ppt/slides/slide{i}.xml"] = sxml.encode("utf-8")
        slide_xmls[f"ppt/slides/_rels/slide{i}.xml.rels"] = rxml.encode("utf-8")

    media_files = {f"ppt/media/{p.name}": p.read_bytes() for p in ASSETS.glob("*.png") if p.name != "contact_sheet.png"}
    skip_prefixes = ("ppt/slides/slide", "ppt/slides/_rels/slide")
    with zipfile.ZipFile(TEMPLATE, "r") as zin, zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        names = set()
        for item in zin.infolist():
            if item.filename.startswith(skip_prefixes):
                continue
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = update_content_types(data, len(SLIDES))
            elif item.filename == "ppt/presentation.xml":
                data = update_presentation(data, len(SLIDES))
            elif item.filename == "ppt/_rels/presentation.xml.rels":
                data = update_presentation_rels(data, len(SLIDES))
            elif item.filename == "docProps/app.xml":
                data = update_app(data, len(SLIDES))
            zout.writestr(item, data)
            names.add(item.filename)
        for name, data in slide_xmls.items():
            zout.writestr(name, data)
        for name, data in media_files.items():
            if name in names:
                continue
            zout.writestr(name, data)


if __name__ == "__main__":
    build()
    print(f"Wrote {OUTPUT}")
