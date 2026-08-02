"""The Bangladesh Railway intercity network RailBot models.

Compiled from publicly documented route information. Train names, numbers and
the stations each service runs through are well attested; the departure times
and the distance and halt figures are representative rather than taken from the
current official timetable, and are marked as such in the README. They exist to
give the Risk Agent's model realistic inputs, not to sell tickets.

Station coordinates are real, so the frontend can project the network onto a
map of the country instead of placing lines by eye.
"""

# name -> (latitude, longitude)
STATIONS = {
    "Dhaka (Kamalapur)": (23.7328, 90.4265),
    "Biman Bandar": (23.8513, 90.4045),
    "Bhairab Bazar": (24.0500, 90.9800),
    "Brahmanbaria": (23.9570, 91.1120),
    "Akhaura": (23.8700, 91.2100),
    "Cumilla": (23.4600, 91.1800),
    "Feni": (23.0200, 91.4000),
    "Chattogram": (22.3400, 91.8300),
    # The station sits east of the town centre, inland of the beach.
    "Cox's Bazar": (21.4419, 92.0105),
    "Srimangal": (24.3100, 91.7300),
    "Sylhet": (24.8990, 91.8700),
    "Kishoreganj": (24.4400, 90.7800),
    "Mymensingh": (24.7500, 90.4000),
    "Mohanganj": (24.8500, 90.9800),
    "Jamalpur": (24.9200, 89.9400),
    "Tangail": (24.2500, 89.9200),
    "Ishwardi": (24.1300, 89.0700),
    "Natore": (24.4100, 88.9900),
    "Rajshahi": (24.3700, 88.6000),
    "Santahar": (24.7900, 88.9900),
    "Bogura": (24.8500, 89.3700),
    "Parbatipur": (25.6600, 88.9200),
    "Dinajpur": (25.6300, 88.6400),
    "Panchagarh": (26.3300, 88.5600),
    "Chilahati": (26.1000, 88.9500),
    "Rangpur": (25.7500, 89.2500),
    "Lalmonirhat": (25.9200, 89.4500),
    "Kurigram": (25.8100, 89.6400),
    "Kushtia": (23.9000, 89.1200),
    "Rajbari": (23.7600, 89.6500),
    "Faridpur": (23.6000, 89.8300),
    "Jashore": (23.1700, 89.2100),
    "Benapole": (23.0400, 88.9400),
    "Khulna": (22.8200, 89.5600),
    "Chandpur": (23.2300, 90.6500),
    "Noakhali": (22.8700, 91.1000),
}

# Corridors the network is built from. Every train's route is a walk along
# these, so the map can draw the whole system once and then light one path.
CORRIDORS = [
    ["Dhaka (Kamalapur)", "Biman Bandar", "Bhairab Bazar", "Brahmanbaria",
     "Akhaura", "Cumilla", "Feni", "Chattogram"],
    ["Chattogram", "Cox's Bazar"],
    ["Akhaura", "Srimangal", "Sylhet"],
    ["Bhairab Bazar", "Kishoreganj"],
    ["Biman Bandar", "Mymensingh", "Jamalpur"],
    ["Mymensingh", "Mohanganj"],
    ["Dhaka (Kamalapur)", "Tangail", "Ishwardi", "Natore", "Rajshahi"],
    ["Natore", "Santahar", "Bogura", "Parbatipur", "Dinajpur", "Panchagarh"],
    ["Parbatipur", "Chilahati"],
    ["Parbatipur", "Rangpur", "Lalmonirhat", "Kurigram"],
    ["Ishwardi", "Kushtia", "Jashore", "Khulna"],
    ["Jashore", "Benapole"],
    ["Dhaka (Kamalapur)", "Rajbari", "Faridpur"],
    ["Cumilla", "Chandpur"],
    ["Feni", "Noakhali"],
]

# name, number, route (station list), distance km, scheduled halts
TRAINS = [
    # ---- Dhaka - Chattogram ----
    ("Subarna Express", "701", ["Dhaka (Kamalapur)", "Biman Bandar", "Feni", "Chattogram"], 320, 4),
    ("Subarna Express", "702", ["Chattogram", "Feni", "Biman Bandar", "Dhaka (Kamalapur)"], 320, 4),
    ("Sonar Bangla Express", "787", ["Dhaka (Kamalapur)", "Biman Bandar", "Feni", "Chattogram"], 320, 4),
    ("Sonar Bangla Express", "788", ["Chattogram", "Feni", "Biman Bandar", "Dhaka (Kamalapur)"], 320, 4),
    ("Mohanagar Provati", "703", ["Dhaka (Kamalapur)", "Biman Bandar", "Brahmanbaria", "Cumilla", "Feni", "Chattogram"], 320, 9),
    ("Mohanagar Godhuli", "704", ["Chattogram", "Feni", "Cumilla", "Brahmanbaria", "Biman Bandar", "Dhaka (Kamalapur)"], 320, 9),
    ("Mohanagar Express", "721", ["Dhaka (Kamalapur)", "Biman Bandar", "Cumilla", "Feni", "Chattogram"], 320, 8),
    ("Mohanagar Express", "722", ["Chattogram", "Feni", "Cumilla", "Biman Bandar", "Dhaka (Kamalapur)"], 320, 8),
    ("Turna Nishitha", "741", ["Dhaka (Kamalapur)", "Biman Bandar", "Brahmanbaria", "Cumilla", "Feni", "Chattogram"], 320, 8),
    ("Turna Nishitha", "742", ["Chattogram", "Feni", "Cumilla", "Brahmanbaria", "Biman Bandar", "Dhaka (Kamalapur)"], 320, 8),
    ("Chattala Express", "802", ["Dhaka (Kamalapur)", "Biman Bandar", "Brahmanbaria", "Cumilla", "Feni", "Chattogram"], 320, 12),

    # ---- Chattogram - Cox's Bazar ----
    ("Cox's Bazar Express", "813", ["Dhaka (Kamalapur)", "Biman Bandar", "Feni", "Chattogram", "Cox's Bazar"], 452, 6),
    ("Cox's Bazar Express", "814", ["Cox's Bazar", "Chattogram", "Feni", "Biman Bandar", "Dhaka (Kamalapur)"], 452, 6),
    ("Parjatak Express", "815", ["Dhaka (Kamalapur)", "Biman Bandar", "Chattogram", "Cox's Bazar"], 452, 5),

    # ---- Dhaka - Sylhet ----
    ("Parabat Express", "709", ["Dhaka (Kamalapur)", "Biman Bandar", "Brahmanbaria", "Akhaura", "Srimangal", "Sylhet"], 319, 11),
    ("Parabat Express", "710", ["Sylhet", "Srimangal", "Akhaura", "Brahmanbaria", "Biman Bandar", "Dhaka (Kamalapur)"], 319, 11),
    ("Upaban Express", "739", ["Dhaka (Kamalapur)", "Biman Bandar", "Akhaura", "Srimangal", "Sylhet"], 319, 10),
    ("Upaban Express", "740", ["Sylhet", "Srimangal", "Akhaura", "Biman Bandar", "Dhaka (Kamalapur)"], 319, 10),
    ("Joyantika Express", "717", ["Dhaka (Kamalapur)", "Biman Bandar", "Brahmanbaria", "Akhaura", "Srimangal", "Sylhet"], 319, 13),
    ("Kalni Express", "773", ["Dhaka (Kamalapur)", "Biman Bandar", "Akhaura", "Srimangal", "Sylhet"], 319, 8),

    # ---- Chattogram - Sylhet ----
    ("Paharika Express", "719", ["Chattogram", "Feni", "Cumilla", "Akhaura", "Srimangal", "Sylhet"], 430, 14),
    ("Udayan Express", "723", ["Sylhet", "Srimangal", "Akhaura", "Cumilla", "Feni", "Chattogram"], 430, 14),

    # ---- Dhaka - Rajshahi ----
    ("Silkcity Express", "753", ["Dhaka (Kamalapur)", "Biman Bandar", "Tangail", "Ishwardi", "Natore", "Rajshahi"], 343, 9),
    ("Silkcity Express", "754", ["Rajshahi", "Natore", "Ishwardi", "Tangail", "Biman Bandar", "Dhaka (Kamalapur)"], 343, 9),
    ("Padma Express", "759", ["Dhaka (Kamalapur)", "Biman Bandar", "Tangail", "Ishwardi", "Natore", "Rajshahi"], 343, 9),
    ("Padma Express", "760", ["Rajshahi", "Natore", "Ishwardi", "Tangail", "Biman Bandar", "Dhaka (Kamalapur)"], 343, 9),
    ("Dhumketu Express", "769", ["Dhaka (Kamalapur)", "Biman Bandar", "Tangail", "Ishwardi", "Rajshahi"], 343, 8),
    ("Banalata Express", "791", ["Dhaka (Kamalapur)", "Biman Bandar", "Ishwardi", "Rajshahi"], 343, 3),

    # ---- Dhaka - Khulna ----
    ("Sundarban Express", "725", ["Dhaka (Kamalapur)", "Biman Bandar", "Ishwardi", "Kushtia", "Jashore", "Khulna"], 405, 11),
    ("Sundarban Express", "726", ["Khulna", "Jashore", "Kushtia", "Ishwardi", "Biman Bandar", "Dhaka (Kamalapur)"], 405, 11),
    ("Chitra Express", "763", ["Dhaka (Kamalapur)", "Biman Bandar", "Ishwardi", "Kushtia", "Jashore", "Khulna"], 405, 13),
    ("Chitra Express", "764", ["Khulna", "Jashore", "Kushtia", "Ishwardi", "Biman Bandar", "Dhaka (Kamalapur)"], 405, 13),
    ("Benapole Express", "795", ["Dhaka (Kamalapur)", "Biman Bandar", "Ishwardi", "Jashore", "Benapole"], 420, 7),

    # ---- Dhaka - north ----
    ("Ekota Express", "705", ["Dhaka (Kamalapur)", "Biman Bandar", "Tangail", "Natore", "Santahar", "Parbatipur", "Dinajpur", "Panchagarh"], 480, 14),
    ("Ekota Express", "706", ["Panchagarh", "Dinajpur", "Parbatipur", "Santahar", "Natore", "Tangail", "Biman Bandar", "Dhaka (Kamalapur)"], 480, 14),
    ("Drutojan Express", "757", ["Dhaka (Kamalapur)", "Biman Bandar", "Tangail", "Santahar", "Parbatipur", "Dinajpur", "Panchagarh"], 480, 13),
    ("Nilsagar Express", "765", ["Dhaka (Kamalapur)", "Biman Bandar", "Tangail", "Santahar", "Parbatipur", "Chilahati"], 460, 13),
    ("Nilsagar Express", "766", ["Chilahati", "Parbatipur", "Santahar", "Tangail", "Biman Bandar", "Dhaka (Kamalapur)"], 460, 13),
    ("Rangpur Express", "771", ["Dhaka (Kamalapur)", "Biman Bandar", "Tangail", "Bogura", "Parbatipur", "Rangpur"], 465, 12),
    ("Kurigram Express", "797", ["Dhaka (Kamalapur)", "Biman Bandar", "Tangail", "Bogura", "Parbatipur", "Rangpur", "Lalmonirhat", "Kurigram"], 500, 15),
    ("Panchagarh Express", "793", ["Dhaka (Kamalapur)", "Biman Bandar", "Tangail", "Santahar", "Parbatipur", "Dinajpur", "Panchagarh"], 480, 11),

    # ---- Dhaka - Mymensingh and Jamalpur ----
    ("Tista Express", "707", ["Dhaka (Kamalapur)", "Biman Bandar", "Mymensingh", "Jamalpur"], 240, 10),
    ("Brahmaputra Express", "743", ["Dhaka (Kamalapur)", "Biman Bandar", "Mymensingh", "Jamalpur"], 240, 12),
    ("Agnibina Express", "735", ["Dhaka (Kamalapur)", "Biman Bandar", "Mymensingh", "Jamalpur"], 240, 11),
    ("Haor Express", "777", ["Dhaka (Kamalapur)", "Biman Bandar", "Mymensingh", "Mohanganj"], 280, 12),

    # ---- Dhaka - Kishoreganj ----
    ("Egarosindhur Provati", "737", ["Dhaka (Kamalapur)", "Biman Bandar", "Bhairab Bazar", "Kishoreganj"], 135, 8),
    ("Egarosindhur Godhuli", "750", ["Kishoreganj", "Bhairab Bazar", "Biman Bandar", "Dhaka (Kamalapur)"], 135, 8),

    # ---- West zone cross-country ----
    ("Rupsha Express", "727", ["Khulna", "Jashore", "Ishwardi", "Natore", "Santahar", "Parbatipur", "Chilahati"], 450, 16),
    ("Sagardari Express", "761", ["Khulna", "Jashore", "Ishwardi", "Rajshahi"], 280, 12),
    ("Barendra Express", "731", ["Rajshahi", "Natore", "Santahar", "Parbatipur", "Chilahati"], 320, 13),
    ("Titumir Express", "733", ["Rajshahi", "Natore", "Santahar", "Parbatipur", "Chilahati"], 320, 12),
    ("Kapotaksha Express", "715", ["Khulna", "Jashore", "Ishwardi", "Rajshahi"], 280, 14),
]
