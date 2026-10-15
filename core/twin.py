from datetime import datetime
import math
import random


class SmartBinSystem:
    def __init__(self):
        self.bins = {
            "BIN-001 (Main Gate)": {
                "lat": 12.9716, "lon": 77.5946, "type": "Mixed",
                "bin_height_cm": 60.0, "inner_length_cm": 40.0, "inner_width_cm": 35.0,
                "ultrasonic_distance_cm": 33.0, "temperature": 24.1, "battery": 81, "emptied_at": "06:10"
            },
            "BIN-002 (Cafeteria)": {
                "lat": 12.9722, "lon": 77.5950, "type": "Plastic",
                "bin_height_cm": 70.0, "inner_length_cm": 50.0, "inner_width_cm": 45.0,
                "ultrasonic_distance_cm": 8.4, "temperature": 19.6, "battery": 63, "emptied_at": "04:45"
            },
            "BIN-003 (Admin Block)": {
                "lat": 12.9710, "lon": 77.5935, "type": "Paper",
                "bin_height_cm": 60.0, "inner_length_cm": 40.0, "inner_width_cm": 40.0,
                "ultrasonic_distance_cm": 48.0, "temperature": 27.8, "battery": 94, "emptied_at": "08:30"
            },
            "BIN-004 (Innovation Hub)": {
                "lat": 12.9705, "lon": 77.5960, "type": "Glass",
                "bin_height_cm": 55.0, "inner_length_cm": 35.0, "inner_width_cm": 35.0,
                "ultrasonic_distance_cm": 45.1, "temperature": 21.3, "battery": 72, "emptied_at": "09:55"
            }
        }
        self.history = []
        for bin_details in self.bins.values():
            self._calculate_fill(bin_details)
        self._record_history()

    def get_all_bins(self):
        """Returns the current snapshot state of the entire bin grid."""
        return self.bins

    def get_history(self):
        return self.history

    @staticmethod
    def _calculate_fill(bin_details):
        height_cm = float(bin_details["bin_height_cm"])
        length_cm = float(bin_details["inner_length_cm"])
        width_cm = float(bin_details["inner_width_cm"])
        distance_cm = max(0.0, min(height_cm, float(bin_details["ultrasonic_distance_cm"])))
        fill_height_cm = height_cm - distance_cm
        capacity_liters = height_cm * length_cm * width_cm / 1000
        fill_volume_liters = fill_height_cm * length_cm * width_cm / 1000
        fill_level = fill_volume_liters / capacity_liters * 100 if capacity_liters else 0

        bin_details.update(
            {
                "ultrasonic_distance_cm": round(distance_cm, 1),
                "fill_height_cm": round(fill_height_cm, 1),
                "capacity_liters": round(capacity_liters, 1),
                "fill_volume_liters": round(fill_volume_liters, 1),
                "fill_level": round(fill_level, 1),
                "status": "Critical" if fill_level >= 85 else "Warning" if fill_level >= 70 else "Normal",
                "sensor_source": "Simulated",
            }
        )

    def update_bin_from_ultrasonic(
        self,
        bin_id,
        distance_cm,
        temperature=None,
        battery=None,
        source="Manual entry",
        record=True,
    ):
        """Update a bin from the measured sensor-to-waste air gap in centimeters."""
        if bin_id not in self.bins:
            return
        distance_cm = float(distance_cm)
        if not math.isfinite(distance_cm) or not 0 <= distance_cm <= 400:
            raise ValueError("Ultrasonic distance must be between 0 and 400 cm.")

        bin_details = self.bins[bin_id]
        bin_details["ultrasonic_distance_cm"] = distance_cm
        if temperature is not None:
            bin_details["temperature"] = float(temperature)
        if battery is not None:
            bin_details["battery"] = max(0, min(100, float(battery)))
        self._calculate_fill(bin_details)
        bin_details["sensor_source"] = source
        if record:
            self._record_history()

    def update_bin_level(self, bin_id, new_level):
        """Set a target fill percentage by converting it to an ultrasonic air gap."""
        if bin_id not in self.bins:
            return
        fill_percent = max(0.0, min(100.0, float(new_level)))
        bin_height = self.bins[bin_id]["bin_height_cm"]
        distance_cm = bin_height * (1 - fill_percent / 100)
        self.update_bin_from_ultrasonic(bin_id, distance_cm)

    def _record_history(self):
        recorded_at = datetime.now()
        for bin_id, bin_details in self.bins.items():
            self.history.append(
                {
                    "recorded_at": recorded_at,
                    "bin_id": bin_id,
                    "fill_percent": bin_details["fill_level"],
                    "fill_volume_liters": bin_details["fill_volume_liters"],
                    "ultrasonic_distance_cm": bin_details["ultrasonic_distance_cm"],
                }
            )
        self.history = self.history[-400:]

    def simulate_realtime_drift(self):
        """Simulate ultrasonic distance, temperature, and battery telemetry."""
        for bin_details in self.bins.values():
            distance = max(0.0, bin_details["ultrasonic_distance_cm"] - random.uniform(0.2, 1.5))
            temperature = bin_details["temperature"] + random.uniform(-0.3, 0.3)
            battery = max(0.0, bin_details["battery"] - random.uniform(0.01, 0.08))
            bin_details["ultrasonic_distance_cm"] = distance
            bin_details["temperature"] = temperature
            bin_details["battery"] = battery
            self._calculate_fill(bin_details)
        self._record_history()