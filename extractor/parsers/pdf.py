import os
import fitz
from ..images import describe_image


def parse_pdf(filepath, out_dir, config):
    doc = fitz.open(filepath)
    name = os.path.basename(filepath)
    img_mode = config["image"]["mode"]
    lines = []

    lines.append(f"\n{'='*80}")
    lines.append(f"FILE: {name}")
    lines.append(f"{'='*80}\n")

    for pno in range(len(doc)):
        page = doc[pno]
        text = page.get_text("text")

        if text.strip():
            lines.append(f"--- Page {pno + 1} ---")
            lines.append(text.strip())
            lines.append("")

        if img_mode != "skip":
            f_cfg = config["image"].get("filter", {})
            min_w = f_cfg.get("min_width", 0)
            min_h = f_cfg.get("min_height", 0)

            imgs = page.get_images(full=True)
            for idx, img in enumerate(imgs):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)

                if pix.width < min_w or pix.height < min_h:
                    print(f"    filtered: {pix.width}x{pix.height} < {min_w}x{min_h}")
                    continue

                img_dir = os.path.join(out_dir, "images", name)
                os.makedirs(img_dir, exist_ok=True)
                rel = os.path.join("images", name, f"page_{pno+1}_img_{idx+1}.png")
                img_path = os.path.join(out_dir, rel)

                if pix.n - pix.alpha < 4:
                    pix.save(img_path)
                else:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                    pix.save(img_path)

                desc = describe_image(img_path, config)
                lines.append(f"  [Image: {rel}]")
                if desc:
                    lines.append(f"  → {desc}")
                lines.append("")

    doc.close()
    return "\n".join(lines)
