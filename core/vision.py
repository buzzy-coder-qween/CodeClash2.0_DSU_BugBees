import json
from pathlib import Path

import cv2
from ultralytics import YOLO

from core.waste_taxonomy import (
    PROJECT_ROOT,
    WASTE_CLASSES,
    get_ewaste_model_path,
    get_waste_model_path,
    map_ewaste_label,
    map_waste_label,
)


class WasteDetector:
    def __init__(self, model_path=None):
        self.model_path = Path(model_path) if model_path else get_waste_model_path()
        self.waste_specific = self.model_path.is_file()
        self.model_mtime_ns = self.model_path.stat().st_mtime_ns if self.waste_specific else None
        self.ewaste_model_path = get_ewaste_model_path()
        self.ewaste_model_mtime_ns = None
        self.ewaste_metadata = {}
        self.metadata = {}

        if self.waste_specific:
            self.model = YOLO(str(self.model_path))
            metadata_path = self.model_path.with_suffix(".metadata.json")
            if metadata_path.is_file():
                self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.model_source = "Fine-tuned waste model"
            supported_classes = self.metadata.get("supported_classes")
            if supported_classes is None:
                model_names = self.model.names.values() if isinstance(self.model.names, dict) else self.model.names
                supported_classes = [map_waste_label(name) for name in model_names]
            self.supported_classes = {name for name in supported_classes if name in WASTE_CLASSES}
        else:
            base_weights = PROJECT_ROOT / "yolov8n.pt"
            self.model = YOLO(str(base_weights) if base_weights.is_file() else "yolov8n.pt")
            self.model_source = "Generic COCO demo model"
            self.supported_classes = set(WASTE_CLASSES)

        self.ewaste_model = None
        if self.ewaste_model_path.is_file():
            self.ewaste_model = YOLO(str(self.ewaste_model_path))
            self.ewaste_model_mtime_ns = self.ewaste_model_path.stat().st_mtime_ns
            self.ewaste_model_source = "Roboflow e-waste model"
            metadata_path = self.ewaste_model_path.with_suffix(".metadata.json")
            if metadata_path.is_file():
                self.ewaste_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        else:
            self.ewaste_model_source = "Not installed"

    def is_current(self):
        current_path = get_waste_model_path()
        current_mtime = current_path.stat().st_mtime_ns if current_path.is_file() else None
        current_ewaste_path = get_ewaste_model_path()
        current_ewaste_mtime = current_ewaste_path.stat().st_mtime_ns if current_ewaste_path.is_file() else None
        return (
            self.model_path == current_path
            and self.model_mtime_ns == current_mtime
            and self.ewaste_model_path == current_ewaste_path
            and self.ewaste_model_mtime_ns == current_ewaste_mtime
        )

    def detect_waste(self, frame, confidence_threshold=0.25):
        candidates = []
        model_sources = [(self.model, False)]
        if self.ewaste_model is not None:
            model_sources.append((self.ewaste_model, True))

        for model, is_ewaste_model in model_sources:
            predictions = model.predict(frame, conf=confidence_threshold, verbose=False)
            for result in predictions:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    label = str(model.names[class_id])
                    if is_ewaste_model:
                        normalized_label = " ".join(label.casefold().replace("_", " ").split())
                        category = map_ewaste_label(normalized_label)
                    else:
                        category = map_waste_label(label)
                        if category is None or category not in self.supported_classes:
                            continue
                    candidates.append((box, label, category, float(box.conf[0])))

        if not candidates:
            return frame, None

        box, label, category, confidence = max(candidates, key=lambda item: item[3])
        annotated_frame = frame.copy()
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            annotated_frame,
            f"{category} ({confidence:.2f})",
            (x1, max(22, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )
        return annotated_frame, {
            "label": label,
            "category": category,
            "confidence": confidence,
        }

    def process_frame(self, frame):
        annotated_frame, detection = self.detect_waste(frame)
        if detection is None:
            return annotated_frame, "No Waste Detected", 0.0
        return annotated_frame, detection["category"], detection["confidence"]

# Quick local test loop
if __name__ == "__main__":
    detector = WasteDetector()
    cap = cv2.VideoCapture(0)
    
    print("Starting webcam... Press 'q' to quit.")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        annotated_frame, item_type, conf = detector.process_frame(frame)
        
        if item_type != "No Waste Detected":
            print(f"Detected: {item_type} with confidence {conf:.2f}")
            
        cv2.imshow("EcoTwin CV Test", annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()