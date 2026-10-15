import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.waste_taxonomy import WASTE_CLASSES, get_waste_model_path


def main():
    parser = argparse.ArgumentParser(description="Fine-tune YOLOv8 on the prepared waste-stream dataset.")
    parser.add_argument(
        "--data",
        type=Path,
        default=PROJECT_ROOT / "datasets" / "processed" / "taco_yolo" / "dataset.yaml",
    )
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--allow-incomplete", action="store_true", help="Train even if one or more waste streams have no labels.")
    args = parser.parse_args()

    if not args.data.is_file():
        parser.error(f"Dataset config not found: {args.data}. Run scripts.prepare_taco first.")
    counts_path = args.data.parent / "class_counts.json"
    if not counts_path.is_file():
        parser.error(f"Class count report not found: {counts_path}. Re-run scripts.prepare_taco.")

    counts = json.loads(counts_path.read_text(encoding="utf-8"))
    train_counts = counts["instances"]["train"]
    unsupported_classes = [class_name for class_name in WASTE_CLASSES if train_counts.get(class_name, 0) == 0]
    if unsupported_classes and not args.allow_incomplete:
        missing = ", ".join(unsupported_classes)
        parser.error(
            f"No training annotations for: {missing}. Add labeled images for those streams, "
            "or use --allow-incomplete for an explicitly experimental model."
        )

    if unsupported_classes:
        print(f"WARNING: model is not validated for these streams: {', '.join(unsupported_classes)}")

    from ultralytics import YOLO

    base_weights = PROJECT_ROOT / "yolov8n.pt"
    if not base_weights.is_file():
        parser.error(f"YOLOv8 starting weights not found: {base_weights}")

    model = YOLO(str(base_weights))
    results = model.train(
        data=str(args.data.resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=0,
        seed=42,
        patience=12,
        project=str(PROJECT_ROOT / "runs" / "waste"),
        name="yolov8n-taco",
        exist_ok=True,
    )
    best_weights = Path(results.save_dir) / "weights" / "best.pt"
    if not best_weights.is_file():
        raise RuntimeError(f"Training finished without best.pt at {best_weights}")

    production_path = get_waste_model_path()
    production_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_weights, production_path)
    metadata_path = production_path.with_suffix(".metadata.json")
    metadata_path.write_text(
        json.dumps(
            {
                "dataset": str(args.data.resolve()),
                "classes": list(WASTE_CLASSES),
                "supported_classes": [class_name for class_name in WASTE_CLASSES if train_counts.get(class_name, 0) > 0],
                "unsupported_classes": unsupported_classes,
                "train_instances": train_counts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Waste model saved to {production_path}")
    print(f"Model metadata saved to {metadata_path}")


if __name__ == "__main__":
    main()