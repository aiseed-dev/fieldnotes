"""Daily weather for the field from the Open-Meteo archive (ERA5-based, no key).

Open-Meteo serves a ~9 km grid; the nearest grid point to the field is about
2 km away at 5 m elevation, close enough for daily rain / temperature context.
The JMA station nearest the field (Tokushima, 71106) is 12 km east, so the grid
value is not worse than the station value for this purpose.

    from fieldnotes.weather import daily_weather
    daily_weather(date(2026, 10, 27))
    -> {'tmax': 25.1, 'tmin': 15.4, 'rain_mm': 2.0, 'sun_h': 10.0, 'et0_mm': 2.9,
        'days_since_rain': 1}

Values are cached under records/weather/<yyyy-mm>.json so the record files
stay reproducible even if the archive is revised later.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

FIELD_LAT = 34.0801
FIELD_LON = 134.4454
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
DAILY = ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
         "precipitation_sum", "sunshine_duration", "et0_fao_evapotranspiration"]
RAIN_DAY_MM = 1.0  # a day with less than this counts as dry for days_since_rain
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0), ERA5 reanalysis"


def fetch_range(start: date, end: date, lat: float = FIELD_LAT, lon: float = FIELD_LON) -> dict[str, dict]:
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "daily": ",".join(DAILY), "timezone": "Asia/Tokyo",
    })
    with urllib.request.urlopen(f"{ARCHIVE}?{q}", timeout=30) as r:
        d = json.load(r)["daily"]
    out = {}
    for i, day in enumerate(d["time"]):
        sun = d["sunshine_duration"][i]
        out[day] = {
            "tmax": d["temperature_2m_max"][i],
            "tmin": d["temperature_2m_min"][i],
            "tmean": d["temperature_2m_mean"][i],
            "rain_mm": d["precipitation_sum"][i],
            "sun_h": None if sun is None else round(sun / 3600, 1),
            "et0_mm": d["et0_fao_evapotranspiration"][i],
        }
    return out


def _cache_path(root: Path, d: date) -> Path:
    return root / "weather" / f"{d:%Y-%m}.json"


def month_weather(root: Path, d: date, refresh: bool = False) -> dict[str, dict]:
    """All days of d's month that the archive has, cached per month."""
    p = _cache_path(root, d)
    cached = json.loads(p.read_text()) if p.exists() else {}
    if not refresh and d.isoformat() in cached:
        return cached
    first = d.replace(day=1)
    last = min(date.today(), (first + timedelta(days=32)).replace(day=1) - timedelta(days=1))
    cached.update(fetch_range(first, last))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cached, ensure_ascii=False, indent=1))
    return cached


def daily_weather(d: date, root: Path = Path("records"), lookback: int = 30) -> dict:
    """The day's values plus days_since_rain (counting back up to `lookback` days)."""
    days = {}
    for m in {d, (d - timedelta(days=lookback))}:
        days.update(month_weather(root, m))
    if d.isoformat() not in days:
        raise KeyError(f"no weather for {d} yet")
    w = dict(days[d.isoformat()])
    since = 0
    cur = d
    while cur.isoformat() in days and (days[cur.isoformat()]["rain_mm"] or 0) < RAIN_DAY_MM and since < lookback:
        since += 1
        cur -= timedelta(days=1)
    w["days_since_rain"] = since
    return w
