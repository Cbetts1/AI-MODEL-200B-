"""aura/tools/weather.py — Free weather lookup tool.

Uses wttr.in (https://wttr.in) which is a public, free-to-use weather service
that requires no API key.  The data is returned as structured JSON.

Usage
-----
    /tool weather London
    /tool weather New York
    /tool weather Tokyo, Japan
"""

from __future__ import annotations

import json

from .registry import Tool

try:
    from .. import __version__ as _AURA_VERSION  # noqa: PLC0415
except Exception:  # noqa: BLE001
    _AURA_VERSION = "0.4.0"


class WeatherTool(Tool):
    """Fetch current weather for a city — no API key required."""

    name = "weather"
    description = "Get current weather for any city (e.g. weather London)"

    def run(self, args: str) -> str:
        city = args.strip()
        if not city:
            return "⚠️  Usage: /tool weather <city name>"

        try:
            import urllib.request  # noqa: PLC0415

            encoded = city.replace(" ", "+")
            url = f"https://wttr.in/{encoded}?format=j1"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"AURA-weather-tool/{_AURA_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            current = data["current_condition"][0]
            area = data["nearest_area"][0]
            area_name = area["areaName"][0]["value"]
            country = area["country"][0]["value"]

            temp_c = current["temp_C"]
            temp_f = current["temp_F"]
            feels_c = current["FeelsLikeC"]
            humidity = current["humidity"]
            desc = current["weatherDesc"][0]["value"]
            wind_kmph = current["windspeedKmph"]
            wind_dir = current["winddir16Point"]
            visibility = current["visibility"]
            uv = current["uvIndex"]

            return (
                f"🌍 **{area_name}, {country}**\n"
                f"🌡️  Temperature: {temp_c}°C / {temp_f}°F (feels like {feels_c}°C)\n"
                f"☁️  Conditions: {desc}\n"
                f"💧 Humidity: {humidity}%\n"
                f"💨 Wind: {wind_kmph} km/h {wind_dir}\n"
                f"👁️  Visibility: {visibility} km\n"
                f"☀️  UV Index: {uv}"
            )

        except Exception as exc:  # noqa: BLE001
            return f"⚠️  Could not fetch weather for '{city}': {exc}"
