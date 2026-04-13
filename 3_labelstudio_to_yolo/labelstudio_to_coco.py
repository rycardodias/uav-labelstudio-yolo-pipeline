import json
from pathlib import Path
from shutil import copy2
from random import Random

# ================================
#            CONFIG
# ================================
group = "001"

# labelstudio_json = Path(fr"P:\pampas_repository_groups\group_{group}\labelstudio_tiles.json")
labelstudio_json = Path(fr"P:\pampas_repository_groups\group_{group}_labels.json")
source_images    = Path(fr"P:\pampas_repository_groups\group_{group}")
output_root      = Path(fr"P:\temporaryFiles\group_{group}_coco")

train_ratio = 0.8
val_ratio   = 0.15
test_ratio  = 0.05
seed = 42

# MAP Label Studio labels → COCO category names
CLASSES = ["pampas"]            # You can expand this list if needed
CAT_ID = {name: i+1 for i, name in enumerate(CLASSES)}
# ================================


def ensure_dirs():
    for split in ["train", "val", "test"]:
        (output_root / split).mkdir(parents=True, exist_ok=True)


def load_ls(json_path):
    print("[INFO] Loading Label Studio annotations...")
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def extract_annotations(data, img_root):
    """
    Returns a list of dicts:
      {
         "file": "image.jpg",
         "width": W,
         "height": H,
         "bboxes": [
             {"cat": "pampas", "bbox": [x,y,w,h]}   # absolute pixels, COCO format
         ]
      }
    """
    records = []
    missing = 0
    total = 0

    for task in data:
        total += 1
        image_url = task["data"].get("image") or task["data"].get("Image")
        if not image_url:
            continue

        img_name = Path(image_url).name
        img_path = img_root / img_name

        if not img_path.exists():
            missing += 1
            continue

        # Try loading width/height from meta
        w = task.get("meta", {}).get("width")
        h = task.get("meta", {}).get("height")

        if w is None or h is None:
            # Fallback: open with PIL
            from PIL import Image
            with Image.open(img_path) as im:
                w, h = im.size

        boxes = []

        for ann in task.get("annotations", []):
            for r in ann.get("result", []):
                if r.get("type") != "rectanglelabels":
                    continue

                label = r["value"]["rectanglelabels"][0]
                if label not in CLASSES:
                    continue  # ignore unknown labels

                # Convert percentages to pixels (COCO expects absolute pixels)
                x = r["value"]["x"] / 100 * w
                y = r["value"]["y"] / 100 * h
                bw = r["value"]["width"]  / 100 * w
                bh = r["value"]["height"] / 100 * h

                boxes.append({
                    "cat": label,
                    "bbox": [x, y, bw, bh]
                })

        if boxes:
            records.append({
                "file": img_name,
                "path": img_path,
                "width": w,
                "height": h,
                "bboxes": boxes
            })

    print(f"[INFO] Total tasks: {total}")
    print(f"[INFO] Missing images: {missing}")
    print(f"[INFO] Annotated samples: {len(records)}")

    return records


def split_indices(n, train_p, val_p, seed):
    rng = Random(seed)
    idx = list(range(n))
    rng.shuffle(idx)

    c1 = int(train_p * n)
    c2 = int((train_p + val_p) * n)

    return idx[:c1], idx[c1:c2], idx[c2:]


def write_coco_json(records, split):
    coco = {
        "images": [],
        "annotations": [],
        "categories": [
            {"id": CAT_ID[name], "name": name} for name in CLASSES
        ]
    }

    ann_id = 1

    for img_id, r in enumerate(records, start=1):
        coco["images"].append({
            "id": img_id,
            "file_name": r["file"],
            "width": r["width"],
            "height": r["height"]
        })

        for b in r["bboxes"]:
            coco["annotations"].append({
                "id": ann_id,
                "image_id": img_id,
                "category_id": CAT_ID[b["cat"]],
                "bbox": b["bbox"],               # [x,y,w,h]
                "area": b["bbox"][2] * b["bbox"][3],
                "iscrowd": 0
            })
            ann_id += 1

    out_file = output_root / f"instances_{split}.json"
    out_file.write_text(json.dumps(coco, indent=2), encoding="utf-8")
    print(f"[INFO] COCO file saved: {out_file}")


def copy_split_images(records, split):
    for r in records:
        dst = output_root / split / r["file"]
        copy2(r["path"], dst)


def main():
    ensure_dirs()

    data = load_ls(labelstudio_json)
    records = extract_annotations(data, source_images)

    if not records:
        print("[ERRO] No annotations found.")
        return

    n = len(records)
    train_idx, val_idx, test_idx = split_indices(n, train_ratio, val_ratio, seed)

    splits = {
        "train": [records[i] for i in train_idx],
        "val":   [records[i] for i in val_idx],
        "test":  [records[i] for i in test_idx]
    }

    # Save images + COCO JSON
    for split, subset in splits.items():
        copy_split_images(subset, split)
        write_coco_json(subset, split)

    print("\n[✅] COCO dataset successfully created!")
    print(f" → Train: {len(splits['train'])}")
    print(f" → Val:   {len(splits['val'])}")
    print(f" → Test:  {len(splits['test'])}")
    print(f"[INFO] Output folder: {output_root}")


if __name__ == "__main__":
    main()
