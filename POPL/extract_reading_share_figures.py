from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parent
PDF_DIR = ROOT / "pdfs"
OUT_DIR = ROOT / "reading_share_assets" / "figures"


@dataclass(frozen=True)
class PaperFigures:
    slug: str
    pdf_name: str
    labels: tuple[str, ...]


PAPERS: tuple[PaperFigures, ...] = (
    PaperFigures(
        "molavi_2026_qmr",
        "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf",
        ("Fig. 1", "Table 1", "Fig. 3", "Fig. 4", "Fig. 5", "Fig. 9", "Fig. 12", "Fig. 16"),
    ),
    PaperFigures(
        "colledan_2025_resource",
        "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf",
        ("Fig. 4", "Fig. 5", "Fig. 6", "Fig. 8", "Fig. 9", "Fig. 13", "Fig. 14"),
    ),
    PaperFigures(
        "abdulla_2026_verification",
        "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf",
        ("Fig. 1", "Fig. 3", "Fig. 5", "Fig. 6", "Fig. 7", "Fig. 9", "Table 1", "Fig. 12", "Fig. 15", "Fig. 16"),
    ),
    PaperFigures(
        "hirata_2025_qurts",
        "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf",
        ("Table 1", "Fig. 1", "Fig. 2", "Fig. 3", "Fig. 4", "Fig. 5", "Fig. 11", "Fig. 12"),
    ),
)


def label_regex(label: str) -> re.Pattern[str]:
    kind, num = label.split()
    if kind.lower().startswith("fig"):
        return re.compile(rf"\b(?:Fig\.?|Figure)\s*{re.escape(num)}\b", re.I)
    return re.compile(rf"\bTable\s*{re.escape(num)}\b", re.I)


def safe_label(label: str) -> str:
    return label.lower().replace(".", "").replace(" ", "_")


def find_caption(page: fitz.Page, pattern: re.Pattern[str]) -> fitz.Rect | None:
    best: fitz.Rect | None = None
    for block in page.get_text("blocks"):
        if len(block) < 5:
            continue
        rect = fitz.Rect(block[:4])
        text = str(block[4]).replace("\n", " ")
        if pattern.search(text):
            if best is None or rect.y0 < best.y0:
                best = rect
    return best


def crop_rect(page: fitz.Page, caption: fitz.Rect, label: str) -> fitz.Rect:
    page_rect = page.rect
    # Most ACM captions sit below the figure/table. Keep enough context above
    # the caption, while avoiding a full-page unreadable thumbnail.
    above = 340 if label.lower().startswith("fig") else 250
    below = 70 if label.lower().startswith("fig") else 190
    top = max(0, caption.y0 - above)
    bottom = min(page_rect.height, caption.y1 + below)
    if bottom - top < 220:
        bottom = min(page_rect.height, top + 260)
    return fitz.Rect(0, top, page_rect.width, bottom)


def render_crop(page: fitz.Page, rect: fitz.Rect, out: Path) -> tuple[int, int]:
    pix = page.get_pixmap(matrix=fitz.Matrix(2.4, 2.4), clip=rect, alpha=False)
    pix.save(out)
    return pix.width, pix.height


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for paper in PAPERS:
        pdf_path = PDF_DIR / paper.pdf_name
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)
        doc = fitz.open(pdf_path)
        for label in paper.labels:
            pat = label_regex(label)
            found: tuple[int, fitz.Rect] | None = None
            for page_idx, page in enumerate(doc):
                caption = find_caption(page, pat)
                if caption is not None:
                    found = (page_idx, caption)
                    break
            if found is None:
                manifest.append({"paper": paper.slug, "label": label, "status": "missing"})
                continue
            page_idx, caption = found
            page = doc[page_idx]
            rect = crop_rect(page, caption, label)
            out = OUT_DIR / f"{paper.slug}_{safe_label(label)}.png"
            width, height = render_crop(page, rect, out)
            manifest.append(
                {
                    "paper": paper.slug,
                    "label": label,
                    "file": str(out.relative_to(ROOT.parent)),
                    "page": page_idx + 1,
                    "size": [width, height],
                    "status": "ok",
                }
            )
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {sum(1 for item in manifest if item.get('status') == 'ok')} figure crops to {OUT_DIR}")


if __name__ == "__main__":
    main()
