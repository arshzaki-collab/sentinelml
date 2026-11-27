"""Constants and authoritative domain configuration for Blind Billion 2.0."""

from datetime import date
from typing import Final

# Financial Invariants
STARTING_BUDGET_USD: Final[int] = 1_000_000_000  # $1,000,000,000 USD
VALUATION_MAX_AGE_DAYS: Final[int] = 180
CANDIDATES_PER_SLOT: Final[int] = 4

# Transfer Windows (Years in which players can be sold and replaced from original shortlist)
TRANSFER_WINDOWS: Final[tuple[int, ...]] = (2019, 2022, 2025)

# Squad Slot Configuration: Exactly 7 Signings
SQUAD_SLOTS: Final[tuple[dict[str, object], ...]] = (
    {"slot_index": 1, "year": 2016, "position": "ST", "description": "Striker (Centre-Forward)"},
    {"slot_index": 2, "year": 2017, "position": "WG", "description": "Winger (LW / RW)"},
    {"slot_index": 3, "year": 2018, "position": "CM", "description": "Central Midfielder"},
    {"slot_index": 4, "year": 2020, "position": "CB", "description": "Centre-Back"},
    {"slot_index": 5, "year": 2021, "position": "CM", "description": "Central Midfielder"},
    {"slot_index": 6, "year": 2023, "position": "CB", "description": "Centre-Back"},
    {"slot_index": 7, "year": 2024, "position": "GK", "description": "Goalkeeper"},
)

# Reference Dates: July 1 of each year from 2016 through 2026
REFERENCE_DATES: Final[dict[int, date]] = {year: date(year, 7, 1) for year in range(2016, 2027)}

# European Central Bank (ECB) Official EUR/USD Foreign Exchange Reference Rates (July 1)
ECB_EUR_USD_RATES: Final[dict[int, float]] = {
    2016: 1.1104,
    2017: 1.1369,
    2018: 1.1685,
    2019: 1.1293,
    2020: 1.1232,
    2021: 1.1845,
    2022: 1.0435,
    2023: 1.0899,
    2024: 1.0745,
    2025: 1.1755,
    2026: 1.1383,
}

# Source Dataset Mirror (Cloudflare R2 Public Mirror of dcaribou/transfermarkt-datasets)
R2_DATASET_BASE_URL: Final[str] = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"

CORE_TABLE_FILES: Final[dict[str, str]] = {
    "competitions": "competitions.csv.gz",
    "games": "games.csv.gz",
    "clubs": "clubs.csv.gz",
    "players": "players.csv.gz",
    "appearances": "appearances.csv.gz",
    "player_valuations": "player_valuations.csv.gz",
    "club_games": "club_games.csv.gz",
    "transfers": "transfers.csv.gz",
}

# European League Competition Codes
EUROPEAN_TOP_FLIGHT_LEAGUES: Final[tuple[str, ...]] = (
    "GB1",  # Premier League (England)
    "ES1",  # La Liga (Spain)
    "IT1",  # Serie A (Italy)
    "L1",  # Bundesliga (Germany)
    "FR1",  # Ligue 1 (France)
    "PO1",  # Liga Portugal (Portugal)
    "NL1",  # Eredivisie (Netherlands)
    "BE1",  # Jupiler Pro League (Belgium)
    "SC1",  # Scottish Premiership (Scotland)
    "TR1",  # Super Lig (Turkey)
)

UEFA_COMPETITIONS: Final[tuple[str, ...]] = (
    "CL",  # UEFA Champions League
    "EL",  # UEFA Europa League
    "UCOL",  # UEFA Conference League
)
