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
        self.depot = {"lat": 12.9716, "lon": 77.5946}
        self.vehicles = {
            "TRUCK-01": {"name": "North Crew", "capacity_liters": 320.0, "status": "Available", "route_id": None},
            "TRUCK-02": {"name": "South Crew", "capacity_liters": 450.0, "status": "Available", "route_id": None},
        }
        self.routes = []
        self.route_sequence = 0
        for bin_details in self.bins.values():
            self._calculate_fill(bin_details)
        self._record_history()

    def get_all_bins(self):
        """Returns the current snapshot state of the entire bin grid."""
        return self.bins

    def get_history(self):
        return self.history

    def get_routes(self):
        return self.routes

    def get_vehicles(self):
        return self.vehicles

    @staticmethod
    def _distance_km(origin, destination):
        mean_latitude = math.radians((origin["lat"] + destination["lat"]) / 2)
        north_km = (destination["lat"] - origin["lat"]) * 111.0
        east_km = (destination["lon"] - origin["lon"]) * 111.0 * math.cos(mean_latitude)
        return math.hypot(north_km, east_km)

    def create_route(self, vehicle_id, bin_ids):
        if vehicle_id not in self.vehicles:
            raise ValueError("Unknown vehicle.")
        vehicle = self.vehicles[vehicle_id]
        if vehicle["status"] != "Available":
            raise ValueError(f"{vehicle_id} is not available.")

        requested_bins = list(dict.fromkeys(bin_ids))
        if not requested_bins:
            raise ValueError("Select at least one bin.")
        if any(bin_id not in self.bins for bin_id in requested_bins):
            raise ValueError("Route contains an unknown bin.")

        total_volume = sum(self.bins[bin_id]["fill_volume_liters"] for bin_id in requested_bins)
        if total_volume <= 0:
            raise ValueError("Selected bins have no estimated waste to collect.")
        if total_volume > vehicle["capacity_liters"]:
            raise ValueError(
                f"Selected load is {total_volume:.1f} L, above {vehicle_id}'s "
                f"{vehicle['capacity_liters']:.1f} L capacity."
            )

        remaining = [bin_id for bin_id in requested_bins if self.bins[bin_id]["fill_volume_liters"] > 0]
        ordered_bins = []
        current_location = self.depot
        while remaining:
            highest_priority = max(
                3 if self.bins[bin_id]["status"] == "Critical"
                else 2 if self.bins[bin_id]["status"] == "Warning"
                else 1
                for bin_id in remaining
            )
            priority_bins = [
                bin_id for bin_id in remaining
                if (3 if self.bins[bin_id]["status"] == "Critical"
                    else 2 if self.bins[bin_id]["status"] == "Warning" else 1) == highest_priority
            ]
            next_bin = min(
                priority_bins,
                key=lambda bin_id: self._distance_km(current_location, self.bins[bin_id]),
            )
            ordered_bins.append(next_bin)
            remaining.remove(next_bin)
            current_location = self.bins[next_bin]

        route_stops = [
            {
                "order": stop_index,
                "bin_id": bin_id,
                "status": "Pending",
                "volume_liters": self.bins[bin_id]["fill_volume_liters"],
            }
            for stop_index, bin_id in enumerate(ordered_bins, start=1)
        ]
        route_distance = self._distance_km(self.depot, self.bins[ordered_bins[0]])
        route_distance += sum(
            self._distance_km(self.bins[first], self.bins[second])
            for first, second in zip(ordered_bins, ordered_bins[1:])
        )
        route_distance += self._distance_km(self.bins[ordered_bins[-1]], self.depot)

        self.route_sequence += 1
        route = {
            "route_id": f"ROUTE-{self.route_sequence:03d}",
            "vehicle_id": vehicle_id,
            "status": "Planned",
            "created_at": datetime.now(),
            "stops": route_stops,
            "total_volume_liters": round(total_volume, 1),
            "estimated_distance_km": round(route_distance, 2),
        }
        self.routes.insert(0, route)
        vehicle["status"] = "Assigned"
        vehicle["route_id"] = route["route_id"]
        return route

    def dispatch_route(self, route_id):
        route = next((item for item in self.routes if item["route_id"] == route_id), None)
        if route is None:
            raise ValueError("Route not found.")
        if route["status"] != "Planned":
            raise ValueError("Only planned routes can be dispatched.")
        route["status"] = "Active"
        route["dispatched_at"] = datetime.now()
        self.vehicles[route["vehicle_id"]]["status"] = "En route"
        return route

    def complete_next_route_stop(self, route_id):
        route = next((item for item in self.routes if item["route_id"] == route_id), None)
        if route is None:
            raise ValueError("Route not found.")
        if route["status"] != "Active":
            raise ValueError("Dispatch the route before completing stops.")

        next_stop = next((stop for stop in route["stops"] if stop["status"] == "Pending"), None)
        if next_stop is None:
            raise ValueError("There are no pending stops on this route.")

        bin_id = next_stop["bin_id"]
        self.update_bin_level(bin_id, 0)
        self.bins[bin_id]["emptied_at"] = datetime.now().strftime("%H:%M")
        next_stop["status"] = "Completed"
        next_stop["completed_at"] = datetime.now()

        if all(stop["status"] == "Completed" for stop in route["stops"]):
            route["status"] = "Completed"
            route["completed_at"] = datetime.now()
            vehicle = self.vehicles[route["vehicle_id"]]
            vehicle["status"] = "Available"
            vehicle["route_id"] = None
        return next_stop

    def cancel_route(self, route_id):
        route = next((item for item in self.routes if item["route_id"] == route_id), None)
        if route is None:
            raise ValueError("Route not found.")
        if route["status"] != "Planned":
            raise ValueError("Only planned routes can be cancelled.")
        route["status"] = "Cancelled"
        vehicle = self.vehicles[route["vehicle_id"]]
        vehicle["status"] = "Available"
        vehicle["route_id"] = None
        return route

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

    # ------------------------------------------------------------------
    # Simulated waste deposit
    # ------------------------------------------------------------------
    _SIMULATED_WASTE_ITEMS = [
        # (item_name,  category,           icon, weight_kg_range)
        ("Plastic Bottle",       "Recyclables",   "🧴",  (0.02, 0.05)),
        ("Aluminium Can",        "Recyclables",   "🥫",  (0.01, 0.03)),
        ("Glass Jar",            "Recyclables",   "🫙",  (0.15, 0.40)),
        ("Broken Glass",         "Recyclables",   "🔷",  (0.05, 0.25)),
        ("Plastic Container",    "Recyclables",   "📦",  (0.03, 0.08)),
        ("Cardboard Box",        "Paper & Card",  "📦",  (0.10, 0.30)),
        ("Newspaper",            "Paper & Card",  "📰",  (0.05, 0.15)),
        ("Egg Carton",           "Paper & Card",  "🥚",  (0.02, 0.04)),
        ("Paper Cup",            "Paper & Card",  "☕",  (0.01, 0.02)),
        ("Tissue Paper",         "Paper & Card",  "🧻",  (0.01, 0.02)),
        ("Banana Peel",          "Organic",       "🍌",  (0.05, 0.12)),
        ("Apple Core",           "Organic",       "🍎",  (0.04, 0.08)),
        ("Food Scraps",          "Organic",       "🍲",  (0.10, 0.35)),
        ("Orange Peel",          "Organic",       "🍊",  (0.06, 0.10)),
        ("Tea Bags",             "Organic",       "🍵",  (0.01, 0.03)),
        ("Old Phone",            "E-Waste",       "📱",  (0.10, 0.20)),
        ("USB Cable",            "E-Waste",       "🔌",  (0.02, 0.05)),
        ("Circuit Board",        "E-Waste",       "🖥️",  (0.05, 0.15)),
        ("Broken Earphones",     "E-Waste",       "🎧",  (0.01, 0.04)),
        ("Old Charger",          "E-Waste",       "🔋",  (0.03, 0.08)),
        ("Battery",              "Hazardous",     "🔋",  (0.02, 0.10)),
        ("Paint Can",            "Hazardous",     "🎨",  (0.20, 0.80)),
        ("Fluorescent Bulb",     "Hazardous",     "💡",  (0.05, 0.12)),
        ("Cigarette Butt",       "Hazardous",     "🚬",  (0.01, 0.01)),
        ("Chemical Spray Can",   "Hazardous",     "⚠️",  (0.10, 0.30)),
        ("Chip Bag",             "Landfill",      "🗑️",  (0.01, 0.03)),
        ("Styrofoam Cup",        "Landfill",      "🥤",  (0.01, 0.02)),
        ("Diaper",               "Landfill",      "🚼",  (0.15, 0.35)),
        ("Broken Ceramic",       "Landfill",      "🍽️",  (0.10, 0.40)),
        ("Old Shoe",             "Landfill",      "👟",  (0.20, 0.50)),
    ]

    _CATEGORY_META = {
        "Recyclables":  {"color": "#24a8d1", "badge": "♻️  RECYCLABLE",   "risk": "Low"},
        "Paper & Card": {"color": "#b58a37", "badge": "📄  PAPER / CARD", "risk": "Low"},
        "Organic":      {"color": "#11a982", "badge": "🌿  ORGANIC",      "risk": "Low"},
        "E-Waste":      {"color": "#8b65bd", "badge": "⚡  E-WASTE",      "risk": "Medium"},
        "Hazardous":    {"color": "#bd4654", "badge": "☣️  HAZARDOUS",    "risk": "High"},
        "Landfill":     {"color": "#657177", "badge": "▣  LANDFILL",     "risk": "Low"},
    }

    def simulate_waste_deposit(self):
        """Simulate a random waste item being dropped into the smartest bin.

        Picks a random waste item, classifies it by category, selects the
        best matching bin (type affinity first, then lowest fill), deposits
        an estimated volume, and returns a dict describing the event.
        """
        item_name, category, icon, (weight_lo, weight_hi) = random.choice(
            self._SIMULATED_WASTE_ITEMS
        )
        weight_kg = round(random.uniform(weight_lo, weight_hi), 3)

        # --- Map category to the closest matching bin type ---
        _TYPE_AFFINITY = {
            "Recyclables":  ("Plastic", "Glass", "Mixed"),
            "Paper & Card": ("Paper", "Mixed"),
            "Organic":      ("Mixed",),
            "E-Waste":      ("Mixed",),
            "Hazardous":    ("Mixed",),
            "Landfill":     ("Mixed",),
        }
        affinity = _TYPE_AFFINITY.get(category, ("Mixed",))

        # Prefer bins whose type matches, then fallback to the least-full bin
        best_bin_id = None
        best_fill = 999
        fallback_bin_id = None
        fallback_fill = 999
        for bin_id, details in self.bins.items():
            current_fill = details.get("fill_level", 0)
            if details.get("type") in affinity and current_fill < best_fill:
                best_bin_id = bin_id
                best_fill = current_fill
            if current_fill < fallback_fill:
                fallback_bin_id = bin_id
                fallback_fill = current_fill

        target_bin_id = best_bin_id or fallback_bin_id
        if target_bin_id is None:
            return None  # no bins (shouldn't happen)

        target = self.bins[target_bin_id]

        # Decrease the ultrasonic air gap to simulate waste added
        deposit_cm = random.uniform(0.5, 2.5)
        new_distance = max(0.0, target["ultrasonic_distance_cm"] - deposit_cm)
        old_fill = target["fill_level"]
        target["ultrasonic_distance_cm"] = new_distance
        self._calculate_fill(target)
        new_fill = target["fill_level"]
        self._record_history()

        meta = self._CATEGORY_META.get(category, self._CATEGORY_META["Landfill"])
        return {
            "item_name": item_name,
            "category": category,
            "icon": icon,
            "weight_kg": weight_kg,
            "bin_id": target_bin_id,
            "bin_short": target_bin_id.split(" (")[0],
            "bin_location": target_bin_id.partition(" (")[2].rstrip(")"),
            "old_fill": round(old_fill, 1),
            "new_fill": round(new_fill, 1),
            "deposit_cm": round(deposit_cm, 1),
            "status": target["status"],
            "badge": meta["badge"],
            "color": meta["color"],
            "risk": meta["risk"],
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }