import json
from pathlib import Path
from shutil import copy2
from random import Random

# ==== CONFIGURAÇÕES ====
group = "005"
# Caminho do ficheiro JSON exportado do Label Studio
labelstudio_json = Path(fr"P:\temporaryFiles\labelstudio_tiles.json")
# labelstudio_json = Path(fr"P:\temporaryFiles\_slices_{group}\labelstudio_tiles.json")

# Pasta onde estão as imagens originais usadas no Label Studio
source_images = Path(fr"P:\temporaryFiles\group_{group}")
# source_images = Path(fr"P:\temporaryFiles\_slices_{group}")

# Pasta raiz do novo dataset YOLO
output_root = Path(fr"P:\temporaryFiles\group_{group}_yolo")
output_images = output_root / "images"
output_labels = output_root / "labels"

# Nome da classe (id 0 = pampas) — mantido para referência
class_name = "pampas"

# Proporções de split
train_ratio = 0.8
val_ratio   = 0.2
test_ratio  = 0

# Semente para reprodutibilidade
seed = 42
# ========================

def ensure_dirs():
    # cria a estrutura base
    for split in ["train", "val", "test"]:
        (output_images / split).mkdir(parents=True, exist_ok=True)
        (output_labels / split).mkdir(parents=True, exist_ok=True)

def load_labelstudio_annotations(json_path: Path):
    print(f"[INFO] A carregar anotações de {json_path}")
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)

def parse_tasks(data, src_root: Path):
    """
    Lê as tasks do Label Studio e devolve uma lista de registos com:
      (src_img_path, image_name, anns_lines)
    Apenas devolve registos com pelo menos uma anotação (YOLO exige .txt; se quiseres incluir imagens sem bbox, podes criar .txt vazio).
    """
    records = []
    missing_images = 0
    total_tasks = 0

    for task in data:
        total_tasks += 1
        # Extrai caminho/nome da imagem (suporta data.image ou data.Image)
        image_field = task["data"].get("image") or task["data"].get("Image")
        if not image_field:
            continue

        image_name = Path(image_field).name
        src_img = src_root / image_name

        if not src_img.exists():
            print(f"[AVISO] Imagem não encontrada: {src_img}")
            missing_images += 1
            continue

        # Extrai anotações
        anns = []
        for ann in task.get("annotations", []):
            for result in ann.get("result", []):
                if result.get("type") != "rectanglelabels":
                    continue
                v = result.get("value", {})
                # Label Studio fornece percentagens (0–100); normalizamos para 0–1
                x, y = v.get("x", 0) / 100, v.get("y", 0) / 100
                w, h = v.get("width", 0) / 100, v.get("height", 0) / 100
                cx, cy = x + w / 2, y + h / 2
                # classe 0 = pampas
                anns.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

        if anns:
            records.append((src_img, image_name, anns))

    print(f"[INFO] Tasks lidas: {total_tasks}")
    if missing_images:
        print(f"[AVISO] Imagens em falta: {missing_images}")

    return records

def split_indices(n, train_p=0.7, val_p=0.2, seed=42):
    rng = Random(seed)
    idx = list(range(n))
    rng.shuffle(idx)

    cut1 = int(train_p * n)
    cut2 = int((train_p + val_p) * n)

    return idx[:cut1], idx[cut1:cut2], idx[cut2:]

def write_yolo_sample(src_img: Path, image_name: str, anns_lines, split: str):
    # Copia imagem
    dst_img = output_images / split / image_name
    copy2(src_img, dst_img)

    # Escreve labels
    dst_lbl = output_labels / split / (Path(image_name).stem + ".txt")
    dst_lbl.write_text("\n".join(anns_lines), encoding="utf-8")

def main():
    output_images.mkdir(parents=True, exist_ok=True)
    output_labels.mkdir(parents=True, exist_ok=True)

    data = load_labelstudio_annotations(labelstudio_json)

    # Cria lista de registos apenas com imagens que têm pelo menos uma bbox
    records = parse_tasks(data, source_images)

    n = len(records)
    if n == 0:
        print("[ERRO] Não foram encontradas anotações com caixas. Nada a fazer.")
        return

    print(f"[INFO] Amostras com anotação: {n}")
    ensure_dirs()

    # Split 70/20/10
    train_idx, val_idx, test_idx = split_indices(
        n, train_p=train_ratio, val_p=val_ratio, seed=seed
    )

    # Grava cada split
    for i in train_idx:
        src_img, image_name, anns = records[i]
        write_yolo_sample(src_img, image_name, anns, "train")

    for i in val_idx:
        src_img, image_name, anns = records[i]
        write_yolo_sample(src_img, image_name, anns, "val")

    for i in test_idx:
        src_img, image_name, anns = records[i]
        write_yolo_sample(src_img, image_name, anns, "test")

    print("[✅] Conversão concluída e divisão aplicada!")
    print(f" → train: {len(train_idx)}")
    print(f" → val:   {len(val_idx)}")
    print(f" → test:  {len(test_idx)}")
    print(f"[INFO] Novo dataset YOLO em: {output_root}")
    print(f"[DICA] Se desejares incluir imagens SEM caixas (labels vazios), avisa que ajusto o script para gerar .txt vazio.")

if __name__ == "__main__":
    main()
