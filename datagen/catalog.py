"""Reference data for the fictional Pacific Isles Auto Group (PIAG).

Everything here is synthetic. Makes/models are real so the photos and price points look credible,
but MSRPs are rounded approximations and the dealer group, rooftops and customers are invented.
"""

from __future__ import annotations

GROUP_NAME = "Pacific Isles Auto Group"

# rooftop_id, name, franchises (new-car brands), lot_capacity
ROOFTOPS = [
    ("R01", "Harbourview Motors", ["Toyota", "Mazda"], 420),
    ("R02", "Northshore Auto", ["Honda", "Subaru"], 360),
    ("R03", "Eastgate Motors", ["Hyundai", "Kia"], 340),
    ("R04", "Ridgeline Ford Chevrolet", ["Ford", "Chevrolet"], 400),
    ("R05", "Bayside Auto Centre", ["Toyota", "Honda"], 380),
    ("R06", "Pacific Isles Certified Pre-Owned", [], 300),
]

# body classes drive elasticity, popularity and segment affinity
# class: (price elasticity to price-to-market gap, base daily sale hazard)
BODY_CLASSES = {
    "compact_car": (17.0, 0.030),
    "midsize_car": (15.0, 0.026),
    "compact_suv": (13.0, 0.034),
    "midsize_suv": (11.5, 0.027),
    "large_suv": (9.0, 0.020),
    "pickup": (10.0, 0.026),
    "minivan": (12.0, 0.021),
    "ev": (19.0, 0.020),
    "performance": (8.0, 0.017),
}

# make, model, body_class, base_msrp_usd, popularity (1.0 = average), wikimedia search hint
MODELS = [
    ("Toyota", "Corolla", "compact_car", 23500, 1.15, "Toyota Corolla E210 sedan"),
    ("Toyota", "Camry", "midsize_car", 29500, 1.10, "2025 Toyota Camry front"),
    ("Toyota", "RAV4", "compact_suv", 31000, 1.30, "2019 Toyota RAV4 front"),
    ("Toyota", "Highlander", "midsize_suv", 41000, 1.00, "Toyota Highlander XU70"),
    ("Toyota", "Tacoma", "pickup", 33000, 1.25, "Toyota Tacoma 2024"),
    ("Toyota", "Tundra", "pickup", 42000, 0.90, "Toyota Tundra 2022"),
    ("Toyota", "Sienna", "minivan", 40000, 0.85, "Toyota Sienna XL40"),
    ("Toyota", "Prius", "compact_car", 29000, 0.95, "Toyota Prius XW60"),
    ("Honda", "Civic", "compact_car", 25000, 1.15, "Honda Civic eleventh generation sedan"),
    ("Honda", "Accord", "midsize_car", 29000, 1.00, "Honda Accord eleventh generation"),
    ("Honda", "CR-V", "compact_suv", 31500, 1.25, "Honda CR-V sixth generation"),
    ("Honda", "HR-V", "compact_suv", 26000, 0.95, "Honda HR-V 2023"),
    ("Honda", "Pilot", "midsize_suv", 42000, 0.90, "2023 Honda Pilot front"),
    ("Honda", "Odyssey", "minivan", 40000, 0.80, "Honda Odyssey fifth generation"),
    ("Hyundai", "Elantra", "compact_car", 22500, 0.95, "Hyundai Elantra CN7"),
    ("Hyundai", "Tucson", "compact_suv", 29000, 1.05, "Hyundai Tucson NX4"),
    ("Hyundai", "Santa Fe", "midsize_suv", 35000, 0.90, "Hyundai Santa Fe MX5"),
    ("Hyundai", "Palisade", "large_suv", 39000, 0.85, "Hyundai Palisade"),
    ("Hyundai", "Ioniq 5", "ev", 43000, 0.80, "Hyundai Ioniq 5"),
    ("Kia", "K4", "compact_car", 22500, 0.85, "Kia K4 2025"),
    ("Kia", "Sportage", "compact_suv", 29000, 1.00, "Kia Sportage NQ5"),
    ("Kia", "Sorento", "midsize_suv", 33000, 0.90, "Kia Sorento MQ4"),
    ("Kia", "Telluride", "large_suv", 38000, 1.05, "Kia Telluride"),
    ("Kia", "EV6", "ev", 43000, 0.70, "Kia EV6"),
    ("Ford", "F-150", "pickup", 40000, 1.20, "2021 Ford F-150 front"),
    ("Ford", "Maverick", "pickup", 27000, 1.10, "Ford Maverick"),
    ("Ford", "Escape", "compact_suv", 30000, 0.85, "Ford Escape 2023"),
    ("Ford", "Explorer", "midsize_suv", 40000, 0.85, "2020 Ford Explorer front"),
    ("Ford", "Bronco", "performance", 40000, 0.95, "Ford Bronco 2021"),
    ("Ford", "Mustang Mach-E", "ev", 41000, 0.65, "Ford Mustang Mach-E"),
    ("Chevrolet", "Silverado 1500", "pickup", 40000, 1.05, "Chevrolet Silverado 1500 2022"),
    ("Chevrolet", "Equinox", "compact_suv", 29000, 0.95, "Chevrolet Equinox 2025"),
    ("Chevrolet", "Trax", "compact_suv", 22000, 1.00, "Chevrolet Trax 2024"),
    ("Chevrolet", "Tahoe", "large_suv", 60000, 0.75, "Chevrolet Tahoe 2021"),
    ("Chevrolet", "Equinox EV", "ev", 35000, 0.70, "Chevrolet Equinox EV"),
    ("Mazda", "Mazda3", "compact_car", 25000, 0.85, "Mazda3 hatchback 2019"),
    ("Mazda", "CX-5", "compact_suv", 30000, 1.05, "Mazda CX-5 KF"),
    ("Mazda", "CX-50", "compact_suv", 32000, 0.90, "Mazda CX-50"),
    ("Mazda", "CX-90", "large_suv", 40000, 0.75, "Mazda CX-90"),
    ("Subaru", "Outback", "midsize_suv", 30000, 1.05, "Subaru Outback BT"),
    ("Subaru", "Forester", "compact_suv", 31000, 1.05, "Subaru Forester SL"),
    ("Subaru", "Crosstrek", "compact_suv", 27000, 1.10, "Subaru Crosstrek 2024"),
    ("Subaru", "WRX", "performance", 34000, 0.70, "Subaru WRX VB"),
]

TRIMS = {
    "compact_car": [("Base", 0.0), ("Sport", 0.08), ("Limited", 0.17)],
    "midsize_car": [("Base", 0.0), ("Sport", 0.07), ("Limited", 0.18)],
    "compact_suv": [("Base", 0.0), ("XLE", 0.09), ("Limited", 0.20)],
    "midsize_suv": [("Base", 0.0), ("Premium", 0.10), ("Platinum", 0.24)],
    "large_suv": [("Base", 0.0), ("Premium", 0.12), ("Platinum", 0.28)],
    "pickup": [("Work", 0.0), ("XLT", 0.14), ("Lariat", 0.30)],
    "minivan": [("Base", 0.0), ("EX", 0.10), ("Touring", 0.22)],
    "ev": [("Standard Range", 0.0), ("Long Range", 0.12), ("Performance", 0.22)],
    "performance": [("Base", 0.0), ("Premium", 0.12), ("Track", 0.25)],
}

COLOURS = [
    ("White", 0.24), ("Black", 0.20), ("Silver", 0.14), ("Grey", 0.17), ("Blue", 0.10),
    ("Red", 0.09), ("Green", 0.03), ("Orange", 0.02), ("Brown", 0.01),
]

# Customer segments and their affinity for each body class (relative propensity to buy)
SEGMENTS = {
    "first_time_buyer": {"compact_car": 2.2, "compact_suv": 1.4, "midsize_car": 0.8, "ev": 0.7},
    "young_family": {"compact_suv": 1.6, "midsize_suv": 1.8, "minivan": 2.4, "large_suv": 1.2},
    "active_lifestyle": {"compact_suv": 1.3, "pickup": 1.5, "performance": 2.2, "ev": 1.4},
    "trades_and_fleet": {"pickup": 3.0, "midsize_suv": 0.6, "compact_car": 0.5},
    "value_retiree": {"midsize_car": 2.0, "compact_suv": 1.2, "midsize_suv": 1.0, "compact_car": 0.9},
}
SEGMENT_MIX = {
    "first_time_buyer": 0.22, "young_family": 0.26, "active_lifestyle": 0.18,
    "trades_and_fleet": 0.12, "value_retiree": 0.22,
}
# ground-truth promo responsiveness: base response multiplier per $1k of offer, by segment
SEGMENT_DISCOUNT_SENSITIVITY = {
    "first_time_buyer": 1.6, "young_family": 1.2, "active_lifestyle": 0.8,
    "trades_and_fleet": 1.0, "value_retiree": 1.4,
}

REGIONS = ["Harbourview", "Northshore", "Eastgate", "Ridgeline", "Bayside", "Uplands", "Westpoint"]

FIRST_NAMES = (
    "James Mary Michael Patricia Robert Jennifer David Linda William Elizabeth Kai Leilani Noah Malia "
    "Liam Olivia Ethan Ava Mason Mia Lucas Chloe Logan Grace Jacob Hana Ryan Emma Daniel Sofia Kenji "
    "Aiko Mateo Isabella Wei Mei Arjun Priya Tomas Lucia Sione Ana Tevita Losa Haruto Yuna Diego Elena"
).split()
LAST_NAMES = (
    "Smith Johnson Williams Brown Jones Garcia Miller Davis Martinez Lopez Wilson Anderson Taylor Thomas "
    "Moore Jackson Martin Lee Thompson White Harris Clark Lewis Robinson Walker Young Allen King Wright "
    "Scott Nguyen Kim Tanaka Sato Chen Wong Patel Reyes Cruz Santos Fonoti Tupou Kealoha Mahoe Silva"
).split()
