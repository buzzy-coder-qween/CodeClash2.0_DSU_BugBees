import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.waste_taxonomy import get_ewaste_model_path


DEFAULT_WORKSPACE = "computer-vision-learning-touhj"
DEFAULT_PROJECT = "capstone-kanon-2"
DEFAULT_VERSION = 4
DATASET_LICENSE = "CC BY 4.0"
DATASET_URL = "https://universe.roboflow.com/computer-vision-learning-touhj/capstone-kanon-2"


def load_dataset(dataset_dir, workspace, project_name, version_number, api_key):
    data_yaml = dataset_dir / "data.yaml"
    if data_yaml.is_file():
        return data_yaml
    if not api_key:
        raise RuntimeError(
            "Set ROBOFLOW_API_KEY in .env or provide an existing YOLO dataset with data.yaml via --dataset-dir."
        )

    from roboflow import Roboflow

    roboflow = Roboflow(api_key=api_key)
    project = roboflow.workspace(workspace).project(project_name)
    version = project.version(version_number)
    dataset = version.download("yolov8", location=str(dataset_dir))
    data_yaml = Path(dataset.location) / "data.yaml"
    if not data_yaml.is_file():
        raise RuntimeError(f"Roboflow export did not contain data.yaml: {data_yaml}")
    return data_yaml


def main():
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(
        description="Download/train the separate e-waste detector and install its checkpoint for the station."
    )
    parser.add_argument("--dataset-dir", type=Path, default=PROJECT_ROOT / "datasets" / "e_waste" / "roboflow")
    parser.add_argument("--workspace", default=os.getenv("ROBOFLOW_EWASTE_WORKSPACE", DEFAULT_WORKSPACE))
    parser.add_argument("--project", default=os.getenv("ROBOFLOW_EWASTE_PROJECT", DEFAULT_PROJECT))
    parser.add_argument("--version", type=int, default=int(os.getenv("ROBOFLOW_EWASTE_VERSION", DEFAULT_VERSION)))
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--min-map50", type=float, default=0.2)
    parser.add_argument("--allow-low-metrics", action="store_true")
    args = parser.parse_args()

    api_key = os.getenv("ROBOFLOW_API_KEY", "").strip()
    try:
        data_yaml = load_dataset(args.dataset_dir, args.workspace, args.project, args.version, api_key)
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    data_config = yaml.safe_load(data_yaml.read_text(encoding="utf-8")) or {}
    names = data_config.get("names", [])
    class_names = list(names.values()) if isinstance(names, dict) else list(names)
    if not class_names:
        parser.error(f"No class names were found in {data_yaml}")

    from ultralytics import YOLO

    base_weights = PROJECT_ROOT / "yolov8n.pt"
    if not base_weights.is_file():
        parser.error(f"YOLOv8 starting weights not found: {base_weights}")

    model = YOLO(str(base_weights))
    training_results = model.train(
        data=str(data_yaml.resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=0,
        seed=42,
        patience=12,
        project=str(PROJECT_ROOT / "runs" / "ewaste"),
        name="ewaste-yolov8n",
        exist_ok=True,
    )
    best_weights = Path(training_results.save_dir) / "weights" / "best.pt"
    if not best_weights.is_file():
        raise RuntimeError(f"Training finished without best.pt at {best_weights}")

    validation_metrics = YOLO(str(best_weights)).val(data=str(data_yaml.resolve()), workers=0)
    map50 = float(validation_metrics.box.map50)
    map50_95 = float(validation_metrics.box.map)
    if map50 < args.min_map50 and not args.allow_low_metrics:
        raise RuntimeError(
            f"E-waste validation mAP50={map50:.3f} is below {args.min_map50:.3f}; "
            "improve data/training or explicitly pass --allow-low-metrics to install anyway."
        )

    model_path = get_ewaste_model_path()
    model_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_weights, model_path)
    metadata_path = model_path.with_suffix(".metadata.json")
    metadata_path.write_text(
        json.dumps(
            {
                "dataset_url": DATASET_URL,
                "dataset_license": DATASET_LICENSE,
                "dataset_workspace": args.workspace,
                "dataset_project": args.project,
                "dataset_version": args.version,
                "classes": class_names,
                "validation_map50": map50,
                "validation_map50_95": map50_95,
                "installed_checkpoint": str(model_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"E-waste weights installed at {model_path}")
    print(f"Validation: mAP50={map50:.3f}, mAP50-95={map50_95:.3f}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()