# UAV Label Studio → YOLO Dataset Preparation Pipeline

This repository provides a reproducible and structured pipeline for preparing UAV imagery datasets for object detection tasks, covering the full workflow from annotation in Label Studio to training-ready datasets in YOLO and COCO formats.

The pipeline was developed in the context of detecting *Cortaderia selloana* (pampas grass), an invasive species in the north-western Iberian Peninsula, but it is fully adaptable to other object detection scenarios involving high-resolution aerial imagery.

---

## 📦 Core Functionality

The repository implements a complete dataset preparation workflow, including:

- Processing of annotations exported from Label Studio (JSON format)
- Image slicing (tiling) to improve small-object detectability
- Conversion of annotations into YOLO and COCO formats
- Generation of reproducible train/validation/test splits

These components enable a consistent transformation from raw UAV imagery to training-ready datasets compatible with modern deep learning frameworks.

---

## 🧩 Repository Structure

- `2_image_slicer/run.py`  
  Image slicing and annotation adjustment module

- `3_labelstudio_to_yolo/labelstudio_to_yolo.py`  
  Conversion from Label Studio JSON to YOLO format

- `3_labelstudio_to_yolo/labelstudio_to_coco.py`  
  Conversion from Label Studio JSON to COCO format (optional)

---

## 🔧 Methodological Overview

### Image Slicing and Annotation Adjustment

High-resolution UAV images are subdivided into smaller tiles (e.g., 640×640 pixels) to enhance detection performance for small and densely distributed objects.

The slicing process:
- preserves spatial consistency of bounding boxes
- adjusts annotations to tile coordinates
- removes invalid or empty annotations
- handles partial overlaps between objects and tile boundaries

This step is particularly relevant for ecological monitoring scenarios where objects exhibit strong scale variability.

---

### Annotation Conversion

Annotations exported from Label Studio are converted into standardized formats:

#### YOLO Format

The pipeline generates a dataset structured as:

    dataset/
    ├── images/
    │   ├── train/
    │   ├── val/
    │   └── test/
    ├── labels/
    │   ├── train/
    │   ├── val/
    │   └── test/

Each annotation file follows the YOLO convention:

  <class_id> <x_center> <y_center> <width> <height>


All coordinates are normalized relative to image dimensions.

---

#### COCO Format (Optional)

The pipeline also supports conversion to COCO format, enabling compatibility with a broader range of detection frameworks and evaluation protocols.

---

## ⚙️ Configuration

The current implementation relies on internal configuration variables defined within each script.

Key parameters include:
- path to Label Studio JSON annotations
- source image directory
- output dataset directory
- dataset split ratios (train/validation/test)
- random seed for reproducibility

⚠️ All paths and parameters must be manually configured prior to execution.

---

## 🚀 Recommended Workflow

1. **Annotation**
   - Annotate UAV images in Label Studio using bounding boxes
   - Export annotations in JSON format

2. **Image Slicing (recommended)**
   ```bash
   python 2_image_slicer/run.py

3. **Conversion to YOLO**
   ```bash
   python 3_labelstudio_to_yolo/labelstudio_to_yolo.py

4. **(Optional) Conversion to COCO**
    ```bash
   python 3_labelstudio_to_yolo/labelstudio_to_coco.py

## 🔁 Reproducibility

The pipeline is designed to support reproducible dataset generation through:

- deterministic processing of annotations  
- fixed random seed for dataset splitting  
- consistent geometric transformation of bounding boxes during slicing  

These properties ensure that dataset preparation can be reliably replicated across different environments.

---

## 🌍 Application Context

This pipeline was used to prepare a UAV-based dataset for detecting *Cortaderia selloana* across diverse environments in northern Portugal and Galicia (Spain), including roadsides, industrial areas, and semi-natural landscapes.

The resulting datasets support research in:

- invasive species monitoring  
- ecological surveying  
- UAV-based computer vision applications  

---

## ⚠️ Limitations

- Scripts rely on manually defined paths (no command-line interface implemented)  
- Designed for bounding-box annotations exported from Label Studio  
- May require adaptation for other annotation schemas or segmentation tasks  

---

## 📄 License

### Dataset
The dataset is released under the Creative Commons Attribution 4.0 International (CC BY 4.0) license.

### Code
The code in this repository is released under the MIT License.

---

## 🤝 Acknowledgements

This work was developed as part of research conducted at:

- Polytechnic Institute of Viana do Castelo (IPVC)  
- atlanTTic Research Center for Telecommunication Technologies, University of Vigo  
