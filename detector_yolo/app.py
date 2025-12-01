import os
from ultralytics import YOLO

def main():
    data_yaml = os.getenv("DATA_YAML", "/data/pampas_dataset.yaml")
    epochs = int(os.getenv("EPOCHS", "50"))
    imgsz = int(os.getenv("IMG_SIZE", "1024"))
    batch = int(os.getenv("BATCH", "8"))
    model_name = os.getenv("MODEL_NAME", "yolov8s.pt")  # base architecture
    project = os.getenv("PROJECT", "/out")
    name = os.getenv("RUN_NAME", "pampas_train")

    print(f"[INFO] Training {model_name} for {epochs} epochs on {data_yaml}")

    model = YOLO(model_name)  # usa arquitetura base (baixada automaticamente)
    model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        project=project,
        name=name,
        device="cpu",  # força CPU
    )

if __name__ == "__main__":
    main()
