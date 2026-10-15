import argparse
import json
import random
import shutil
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.waste_taxonomy import WASTE_CLASSES, map_waste_label


TACO_ANNOTATIONS_URL = "https://raw.githubusercontent.com/pedropro/TACO/master/data/annotations.json"


def fetch_annotations(annotation_path):
    annotation_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        TACO_ANNOTATIONS_URL,
        headers={"User-Agent": "EcoTwin-Waste-Research/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        annotation_path.write_bytes(response.read())


def download_image(image_record, image_path):
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_url = image_record.get("flickr_url")
    if not image_url:
        return False

    request = urllib.request.Request(
        image_url,
        headers={"User-Agent": "EcoTwin-Waste-Research/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            image_path.write_bytes(response.read())
        with Image.open(image_path) as image:
            image.verify()
        return True
    except (OSError, urllib.error.URLError, urllib.error.HTTPError):
        image_path.unlink(missing_ok=True)
        return False


def reset_generated_output(output_dir):
    manifest_path = output_dir / ".taco_generated.json"
    if not output_dir.exists():
        return
    if not manifest_path.exists():
        if any(output_dir.iterdir()):
            raise RuntimeError(
                f"Refusing to overwrite non-generated data in {output_dir}. Choose another --output-dir."
            )
        return
    for relative_path in json.loads(manifest_path.read_text(encoding="utf-8")):
        generated_path = output_dir / relative_path
        if generated_path.is_file():
            generated_path.unlink()
    manifest_path.unlink(missing_ok=True)


def prepare_dataset(annotations, image_root, output_dir, validation_fraction=0.2, limit=None, seed=42):
    categories = {category["id"]: category["name"] for category in annotations["categories"]}
    class_ids = {class_name: index for index, class_name in enumerate(WASTE_CLASSES)}
    image_records = sorted(annotations["images"], key=lambda image: image["id"])
    if limit is not None:
        image_records = image_records[:limit]

    annotations_by_image = defaultdict(list)
    for annotation in annotations["annotations"]:
        category_name = categories.get(annotation["category_id"])
        waste_class = map_waste_label(category_name) if category_name else None
        if waste_class:
            annotations_by_image[annotation["image_id"]].append((annotation, class_ids[waste_class]))

    eligible_images = [image for image in image_records if annotations_by_image.get(image["id"])]
    if not eligible_images:
        raise RuntimeError("No annotated images with mapped waste categories were found.")

    random.Random(seed).shuffle(eligible_images)
    validation_count = max(1, round(len(eligible_images) * validation_fraction)) if len(eligible_images) > 1 else 0
    split_images = {
        "train": eligible_images[validation_count:],
        "val": eligible_images[:validation_count],
    }
    generated_files = []
    class_counts = {split: Counter() for split in split_images}
    processed_image_count = {split: 0 for split in split_images}
    reset_generated_output(output_dir)

    for split_name, split_records in split_images.items():
        for image_record in split_records:
            relative_source = Path(image_record["file_name"])
            if relative_source.is_absolute() or ".." in relative_source.parts:
                continue
            source_path = image_root / relative_source
            if not source_path.is_file():
                continue

            try:
                with Image.open(source_path) as image:
                    image_width, image_height = image.size
                    image.verify()
            except (OSError, ValueError):
                continue
            if not image_width or not image_height:
                continue

            output_name = f"{image_record['id']:06d}_{relative_source.name}"
            image_output = output_dir / "images" / split_name / output_name
            label_output = output_dir / "labels" / split_name / f"{Path(output_name).stem}.txt"
            image_output.parent.mkdir(parents=True, exist_ok=True)
            label_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, image_output)

            label_lines = []
            for annotation, class_id in annotations_by_image[image_record["id"]]:
                x, y, width, height = annotation.get("bbox", (0, 0, 0, 0))
                x1 = max(0.0, min(float(image_width), float(x)))
                y1 = max(0.0, min(float(image_height), float(y)))
                x2 = max(0.0, min(float(image_width), float(x) + float(width)))
                y2 = max(0.0, min(float(image_height), float(y) + float(height)))
                box_width = x2 - x1
                box_height = y2 - y1
                if box_width <= 0 or box_height <= 0:
                    continue
                center_x = (x1 + x2) / 2 / image_width
                center_y = (y1 + y2) / 2 / image_height
                normalized_width = box_width / image_width
                normalized_height = box_height / image_height
                label_lines.append(
                    f"{class_id} {center_x:.6f} {center_y:.6f} {normalized_width:.6f} {normalized_height:.6f}"
                )
                class_counts[split_name][WASTE_CLASSES[class_id]] += 1

            if not label_lines:
                image_output.unlink(missing_ok=True)
                continue
            label_output.write_text("\n".join(label_lines) + "\n", encoding="utf-8")
            generated_files.extend(
                [
                    image_output.relative_to(output_dir).as_posix(),
                    label_output.relative_to(output_dir).as_posix(),
                ]
            )
            processed_image_count[split_name] += 1

    if not processed_image_count["train"] or not processed_image_count["val"]:
        raise RuntimeError(
            "Both train and validation images are required. Download TACO images first or increase --limit."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_config = {
        "path": output_dir.resolve().as_posix(),
        "train": "images/train",
        "val": "images/val",
        "names": list(WASTE_CLASSES),
    }
    config_path = output_dir / "dataset.yaml"
    config_path.write_text(json.dumps(dataset_config, indent=2), encoding="utf-8")
    counts_path = output_dir / "class_counts.json"
    counts_path.write_text(
        json.dumps(
            {
                "classes": list(WASTE_CLASSES),
                "images": processed_image_count,
                "instances": {split: dict(counts) for split, counts in class_counts.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    generated_files.extend(["dataset.yaml", "class_counts.json"])
    (output_dir / ".taco_generated.json").write_text(json.dumps(generated_files, indent=2), encoding="utf-8")

    print(f"Prepared {processed_image_count['train']} train and {processed_image_count['val']} validation images.")
    for class_name in WASTE_CLASSES:
        count = class_counts["train"][class_name] + class_counts["val"][class_name]
        print(f"{class_name}: {count} annotated objects")
    if class_counts["train"]["E-Waste"] + class_counts["val"]["E-Waste"] == 0:
        print("WARNING: TACO has no E-Waste examples. Add a labeled e-waste dataset before production use.")
    print(f"Dataset config: {config_path}")
    return config_path


def main():
    parser = argparse.ArgumentParser(description="Download and convert TACO COCO annotations to YOLO format.")
    parser.add_argument("--dataset-root", type=Path, default=PROJECT_ROOT / "datasets" / "taco" / "raw")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "datasets" / "processed" / "taco_yolo")
    parser.add_argument("--annotations", type=Path, help="COCO JSON; combine supplemental e-waste labels here.")
    parser.add_argument("--images-dir", type=Path, help="Directory containing images referenced by the COCO JSON.")
    parser.add_argument("--download-images", action="store_true", help="Download TACO Flickr images; this may take time.")
    parser.add_argument("--limit", type=int, help="Limit image records for a quick smoke test.")
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not 0 < args.validation_fraction < 1:
        parser.error("--validation-fraction must be between 0 and 1.")
    if args.limit is not None and args.limit < 2:
        parser.error("--limit must be at least 2 to create train and validation splits.")

    annotation_path = args.annotations or args.dataset_root / "annotations.json"
    if not annotation_path.exists():
        if args.annotations:
            parser.error(f"COCO annotations not found: {annotation_path}")
        print(f"Downloading TACO annotations to {annotation_path}")
        fetch_annotations(annotation_path)
    annotations = json.loads(annotation_path.read_text(encoding="utf-8"))

    image_root = args.images_dir or args.dataset_root / "images"
    if args.download_images:
        records = sorted(annotations["images"], key=lambda image: image["id"])
        if args.limit is not None:
            records = records[: args.limit]
        failed_downloads = []
        for index, image_record in enumerate(records, start=1):
            relative_path = Path(image_record["file_name"])
            if relative_path.is_absolute() or ".." in relative_path.parts:
                failed_downloads.append(image_record["file_name"])
                continue
            image_path = image_root / relative_path
            if not image_path.is_file() and not download_image(image_record, image_path):
                failed_downloads.append(image_record["file_name"])
            if index % 50 == 0:
                print(f"Checked/downloaded {index}/{len(records)} images; unavailable: {len(failed_downloads)}")
            time.sleep(0.05)
        print(f"Unavailable images: {len(failed_downloads)}")

    prepare_dataset(
        annotations,
        image_root,
        args.output_dir,
        validation_fraction=args.validation_fraction,
        limit=args.limit,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()