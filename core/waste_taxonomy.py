import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WASTE_CLASSES = (
    "Recyclables",
    "Paper & Card",
    "Organic",
    "E-Waste",
    "Hazardous",
    "Landfill",
)

TACO_TO_STREAM = {
    "aluminium foil": "Recyclables",
    "other plastic bottle": "Recyclables",
    "clear plastic bottle": "Recyclables",
    "glass bottle": "Recyclables",
    "plastic bottle cap": "Recyclables",
    "metal bottle cap": "Recyclables",
    "broken glass": "Recyclables",
    "food can": "Recyclables",
    "aerosol": "Recyclables",
    "drink can": "Recyclables",
    "disposable plastic cup": "Recyclables",
    "glass cup": "Recyclables",
    "other plastic cup": "Recyclables",
    "glass jar": "Recyclables",
    "plastic lid": "Recyclables",
    "metal lid": "Recyclables",
    "other plastic": "Recyclables",
    "plastic film": "Recyclables",
    "six pack rings": "Recyclables",
    "garbage bag": "Recyclables",
    "other plastic wrapper": "Recyclables",
    "single-use carrier bag": "Recyclables",
    "polypropylene bag": "Recyclables",
    "crisp packet": "Recyclables",
    "spread tub": "Recyclables",
    "tupperware": "Recyclables",
    "disposable food container": "Recyclables",
    "other plastic container": "Recyclables",
    "plastic glooves": "Recyclables",
    "plastic utensils": "Recyclables",
    "pop tab": "Recyclables",
    "scrap metal": "Recyclables",
    "squeezable tube": "Recyclables",
    "plastic straw": "Recyclables",
    "toilet tube": "Paper & Card",
    "other carton": "Paper & Card",
    "egg carton": "Paper & Card",
    "drink carton": "Paper & Card",
    "corrugated carton": "Paper & Card",
    "meal carton": "Paper & Card",
    "pizza box": "Paper & Card",
    "paper cup": "Paper & Card",
    "magazine paper": "Paper & Card",
    "tissues": "Paper & Card",
    "wrapping paper": "Paper & Card",
    "normal paper": "Paper & Card",
    "paper bag": "Paper & Card",
    "paper straw": "Paper & Card",
    "food waste": "Organic",
    "battery": "Hazardous",
    "cigarette": "Hazardous",
    "aluminium blister pack": "Landfill",
    "carded blister pack": "Landfill",
    "foam cup": "Landfill",
    "plastified paper bag": "Landfill",
    "rope & strings": "Landfill",
    "shoe": "Landfill",
    "styrofoam piece": "Landfill",
    "unlabeled litter": "Landfill",
}

COCO_TO_STREAM = {
    "bottle": "Recyclables",
    "cup": "Recyclables",
    "fork": "Recyclables",
    "spoon": "Recyclables",
    "knife": "Hazardous",
    "book": "Paper & Card",
    "banana": "Organic",
    "apple": "Organic",
    "sandwich": "Organic",
    "orange": "Organic",
    "broccoli": "Organic",
    "carrot": "Organic",
    "hot dog": "Organic",
    "pizza": "Organic",
    "donut": "Organic",
    "cake": "Organic",
    "cell phone": "E-Waste",
    "phone": "E-Waste",
    "mobile phone": "E-Waste",
    "electronics": "E-Waste",
    "electronic waste": "E-Waste",
    "computer": "E-Waste",
    "tablet": "E-Waste",
    "laptop": "E-Waste",
    "keyboard": "E-Waste",
    "mouse": "E-Waste",
    "tv": "E-Waste",
    "remote": "E-Waste",
}


def map_waste_label(label):
    normalized_label = " ".join(str(label).strip().casefold().split())
    for waste_class in WASTE_CLASSES:
        if normalized_label == waste_class.casefold():
            return waste_class
    return TACO_TO_STREAM.get(normalized_label, COCO_TO_STREAM.get(normalized_label))


def map_ewaste_label(label):
    normalized_label = " ".join(str(label).strip().casefold().replace("_", " ").split())
    if normalized_label in {"battery", "batteries", "lithium battery", "battery pack"}:
        return "Hazardous"
    return "E-Waste"


def get_waste_model_path():
    configured_path = os.getenv("WASTE_MODEL_PATH")
    model_path = Path(configured_path) if configured_path else PROJECT_ROOT / "models" / "waste_yolov8n.pt"
    return model_path if model_path.is_absolute() else PROJECT_ROOT / model_path


def get_ewaste_model_path():
    configured_path = os.getenv("EWASTE_MODEL_PATH")
    model_path = Path(configured_path) if configured_path else PROJECT_ROOT / "models" / "ewaste_yolov8n.pt"
    return model_path if model_path.is_absolute() else PROJECT_ROOT / model_path