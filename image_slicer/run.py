import argparse
import json
import os
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# ---------- utils ----------

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def intersect(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    iw = max(0, x2 - x1)
    ih = max(0, y2 - y1)
    return x1, y1, iw, ih

# ---------- load Label Studio export ----------

def load_labelstudio(ls_json_path: Path, images_dir: Path):
    """
    Returns: dict[filename] = {"size": (W,H), "anns": [{"cls": str, "xywh_norm": (x,y,w,h)}]}
    Accepts common LS shapes (annotations/completions) and percentage coords (0..100).
    """
    with open(ls_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Some exports wrap tasks
    if isinstance(data, dict):
        data = data.get("tasks", []) or data.get("data", []) or data.get("results", []) or []

    store = {}

    for task in data:
        # image path field
        d = task.get("data", {})
        img_key = None
        for k in ("image", "img", "imageUrl", "ocr"):
            if k in d:
                img_key = d[k]
                break
        if not img_key:
            img_key = task.get("image")
        if not img_key:
            continue

        fname = os.path.basename(img_key)

        # collect results
        results = []
        for ann in task.get("annotations", []):
            if "result" in ann:
                results.extend(ann["result"])
        for comp in task.get("completions", []):
            if "result" in comp:
                results.extend(comp["result"])

        anns = []
        for r in results:
            if r.get("type") not in ("rectanglelabels", "labels", "rectanglabels"):
                continue
            v = r.get("value", {})
            rectlabs = v.get("rectanglelabels") or v.get("labels")
            if not rectlabs:
                continue
            cls = rectlabs[0]
            # LS usually stores percentages (0..100)
            x = float(v.get("x", 0.0)) / 100.0
            y = float(v.get("y", 0.0)) / 100.0
            w = float(v.get("width", 0.0)) / 100.0
            h = float(v.get("height", 0.0)) / 100.0
            if w > 0 and h > 0:
                anns.append({"cls": cls, "xywh_norm": (x, y, w, h)})

        store.setdefault(fname, {"size": None, "anns": []})
        store[fname]["anns"].extend(anns)

    # fill sizes, drop missing
    drop = []
    for fname in list(store.keys()):
        p = images_dir / fname
        if not p.exists():
            cands = list(images_dir.glob(f"{Path(fname).stem}.*"))
            if cands:
                p = cands[0]
        if not p.exists():
            drop.append(fname)
            continue
        try:
            with Image.open(p) as im:
                store[fname]["size"] = (im.width, im.height)
        except Exception:
            drop.append(fname)
    for k in drop:
        del store[k]

    return store

# ---------- main (flat + LS JSON only) ----------

def main():
    ap = argparse.ArgumentParser(description="Slice large images and export a single Label Studio JSON with all tiles.")
    ap.add_argument("--root", type=str, required=True, help="Root dir containing images")
    ap.add_argument("--images-subdir", dest="images_subdir", type=str, default="images",
                    help="Subfolder with images relative to --root (use '.' if images are directly under root)")
    ap.add_argument("--labelstudio-json", type=str, required=True,
                    help="Path to the Label Studio export JSON (container path)")
    ap.add_argument("--out", type=str, required=True, help="Output directory")
    ap.add_argument("--slice-size", type=int, default=1024)
    ap.add_argument("--overlap", type=float, default=0.20, help="0.0..0.9 (fraction of tile size)")
    ap.add_argument("--min-visible", dest="min_visible", type=float, default=0.20,
                    help="Min visible fraction of original bbox kept on a tile")
    ap.add_argument("--drop-tiny", dest="drop_tiny", type=int, default=4,
                    help="Drop bboxes < N px after clipping")
    ap.add_argument("--keep-negatives", dest="keep_negatives", action="store_true",
                    help="Keep tiles without objects")
    
    ap.add_argument("--ls-url", type=str, default="http://localhost:8080", help="Base URL of Label Studio (scheme+host). Ex: http://localhost:8080")
    ap.add_argument("--ls-root", type=str, default="pampas_repository/_slices", help="Path under /label-studio/files that maps to your OUT dir, e.g. pampas_repository/_slices")
    args = ap.parse_args()

    root = Path(args.root)
    images_dir = root / args.images_subdir
    out_root = Path(args.out)
    img_out = out_root

    ensure_dir(out_root)
    ensure_dir(img_out)

    ann_map = load_labelstudio(Path(args.labelstudio_json), images_dir)
    files = list(ann_map.keys())

    step = max(1, int(args.slice_size * (1.0 - args.overlap)))
    ls_tasks = []
    total_tiles = 0

    for fname in tqdm(sorted(files), desc="Slicing"):
        src = images_dir / fname
        if not src.exists():
            cands = list(images_dir.glob(f"{Path(fname).stem}.*"))
            if cands:
                src = cands[0]
        if not src.exists():
            continue

        with Image.open(src) as im:
            W, H = im.width, im.height
            # absolute boxes
            abs_anns = []
            for a in ann_map.get(fname, {}).get("anns", []):
                x, y, w, h = a["xywh_norm"]
                abs_anns.append({"cls": a["cls"], "xywh": (x * W, y * H, w * W, h * H)})

            y0 = 0
            while y0 < H:
                x0 = 0
                tile_h = min(args.slice_size, H - y0)
                while x0 < W:
                    tile_w = min(args.slice_size, W - x0)

                    crop = im.crop((x0, y0, x0 + tile_w, y0 + tile_h))
                    stem = Path(fname).stem
                    tile_name = f"{stem}_x{x0}_y{y0}.jpg"
                    crop.save(img_out / tile_name, quality=95)

                    results = []
                    for a in abs_anns:
                        bx, by, bw, bh = a["xywh"]
                        ix, iy, iw, ih = intersect((bx, by, bw, bh), (x0, y0, tile_w, tile_h))
                        if iw <= 0 or ih <= 0:
                            continue
                        inter_area = iw * ih
                        box_area = bw * bh if bw > 0 and bh > 0 else 0
                        if box_area == 0 or inter_area / box_area < args.min_visible:
                            continue
                        if iw < args.drop_tiny or ih < args.drop_tiny:
                            continue

                        # LS expects percentages (0..100) relative to the tile
                        px = (ix - x0) * 100.0 / tile_w
                        py = (iy - y0) * 100.0 / tile_h
                        pw = iw * 100.0 / tile_w
                        ph = ih * 100.0 / tile_h
                        results.append({
                            "id": f"{tile_name}_{len(results)}",
                            "type": "rectanglelabels",
                            "from_name": "label",
                            "to_name": "image",
                            "value": {
                                "x": px, "y": py, "width": pw, "height": ph,
                                "rectanglelabels": [a["cls"]]
                            },
                            "origin": "manual"
                        })

                    if results or args.keep_negatives:
                        web_path = f"{args.ls_root}/{tile_name}"
                        full_url = f"{args.ls_url}/data/local-files/?d={web_path}"
                        ls_tasks.append({
                            "data": {"image": full_url},
                            "annotations": [{"result": results}]
                        })
                        total_tiles += 1

                    x0 += step if x0 + step < W else W
                y0 += step if y0 + step < H else H

    out_json = out_root / "labelstudio_tiles.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(ls_tasks, f, ensure_ascii=False)

    print("\n=== Summary ===")
    print(f"Tiles saved: {total_tiles}")
    print(f"Images dir : {img_out}")
    print(f"LS JSON    : {out_json}")

if __name__ == "__main__":
    main()
