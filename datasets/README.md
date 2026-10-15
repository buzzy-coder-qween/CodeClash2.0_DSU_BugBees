# Waste Model Dataset Workflow

The app uses the TACO (Trash Annotations in Context) dataset as a starting point. TACO provides COCO-format object annotations and images of litter in varied environments. The upstream repository reports 1,500 images and notes that many categories are long-tail. Dataset images are fetched from their original URLs; availability can vary.

## Prepare the Dataset

From the project root, activate `.venv`, then run:

```powershell
python -m scripts.prepare_taco --download-images
```

The command downloads annotations and images, makes a reproducible train/validation split, converts COCO boxes to YOLO labels, and writes `datasets/processed/taco_yolo/dataset.yaml` plus class-count reports. For a small connectivity/conversion check, use `--limit 20`.

## Add Missing Streams

TACO has no E-Waste class. Batteries are mapped to Hazardous, not E-Waste. A model trained only on TACO cannot reliably recognize electronics. Add locally collected, correctly labeled e-waste images to a COCO-format annotation set, merge those records with the TACO annotations, and pass the merged annotation and image paths:

```powershell
python -m scripts.prepare_taco --annotations datasets/combined/annotations.json --images-dir datasets/combined/images --output-dir datasets/processed/waste_yolo
```

COCO categories such as `phone`, `mobile phone`, `electronics`, `electronic waste`, `computer`, `tablet`, `laptop`, `keyboard`, `mouse`, `tv`, and `remote` map to E-Waste. Use local disposal rules when reviewing category mappings. Check the TACO source and individual image terms before redistribution or publication.

## Train and Activate

Training refuses to install a production model if a stream has no training examples:

```powershell
python -m scripts.train_waste_model --data datasets/processed/waste_yolo/dataset.yaml
```

The training command fine-tunes the local `yolov8n.pt`, runs validation, and saves the best checkpoint to `models/waste_yolov8n.pt`. The segregation station automatically prefers this checkpoint. It keeps the generic COCO model as a clearly labeled demo fallback until trained weights exist. `--allow-incomplete` is for experiments only; missing classes are marked unsupported in model metadata and will not be routed by the trained detector.

TACO and locally added data are not guaranteed to match this project's camera, lighting, waste condition, or municipal recycling rules. Review validation metrics and test real intake images before relying on automated routing.

## Separate E-Waste Stream

The e-waste station uses the Roboflow Universe `capstone-kanon-2` object-detection dataset (10,000 images, 20 electronic/appliance classes, CC BY 4.0). The app trains this as a separate model so electronics labels do not need to be mixed into TACO's classes. Batteries detected by that model route to Hazardous; other classes route to E-Waste.

1. Create a Roboflow API key and place it in your local, ignored `.env` file as `ROBOFLOW_API_KEY=...`. Do not commit the key.
2. Stop all running Python/Streamlit processes, then install the optional training dependencies with `python -m pip install -r requirements-ewaste.txt`. On Windows, running processes can lock OpenCV's native DLL during installation.
3. Download, train, validate, and install the e-waste checkpoint:

```powershell
python -m scripts.train_ewaste_model --epochs 60 --batch 8
```

The script downloads the configured Roboflow version to `datasets/e_waste/roboflow`, evaluates validation mAP50, and installs `models/ewaste_yolov8n.pt` only when mAP50 is at least 0.20. Override with `--allow-low-metrics` only for experiments. Model metrics and class names are stored beside the checkpoint as metadata.

The Roboflow key is required to export dataset files. The dataset license is CC BY 4.0; retain its attribution if redistributing trained weights or dataset-derived artifacts. This model complements, but does not replace, the separate general waste-stream detector.