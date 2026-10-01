import re
import time

import pandas as pd
import requests

COUNTIES = [
    {"county": "San Francisco", "state": "CA", "fips": "06075", "lat": 37.7749, "lon": -122.4194},
    {"county": "San Mateo", "state": "CA", "fips": "06081", "lat": 37.5630, "lon": -122.3255},
    {"county": "Santa Cruz", "state": "CA", "fips": "06087", "lat": 36.9741, "lon": -122.0308},
    {"county": "San Luis Obispo", "state": "CA", "fips": "06079", "lat": 35.2828, "lon": -120.6596},
    {"county": "Monterey", "state": "CA", "fips": "06053", "lat": 36.6002, "lon": -121.8947},
    {"county": "Santa Barbara", "state": "CA", "fips": "06083", "lat": 34.4208, "lon": -119.6982},
    {"county": "Ventura", "state": "CA", "fips": "06111", "lat": 34.2805, "lon": -119.2945},
    {"county": "Los Angeles", "state": "CA", "fips": "06037", "lat": 34.0522, "lon": -118.2437},
    {"county": "Orange", "state": "CA", "fips": "06059", "lat": 33.7175, "lon": -117.8311},
    {"county": "San Diego", "state": "CA", "fips": "06073", "lat": 32.8668, "lon": -117.1410},
]

HEADERS = {"User-Agent": "crisis-responder-demo/0.1 (educational portfolio project)"}

HOURLY_CSV = "weather_hourly.csv"
CLEAN_CSV = "weather_clean.csv"
HISTORICAL_CSV = "weather_historical.csv"

# Open-Meteo Historical (ERA5 archive) API -- free, no key needed
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
START_YEAR = 2015
END_YEAR = 2025

HISTORICAL_DAILY_VARS = [
    "temperature_2m_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "precipitation_sum",
]

# Humidity is requested hourly and reduced to a daily minimum ourselves,
# which works regardless of which daily humidity aggregates the API offers.
HISTORICAL_HOURLY_VARS = ["relative_humidity_2m"]


# ---------------------------------------------------------------------------
# Ingest: pull hourly forecasts from the NWS API
# ---------------------------------------------------------------------------

def get_forecastURL(lat, lon):
    '''
    convert latitude and longitude into a NWS forecast endpoint
    gets hourly weather
    '''
    url = f"https://api.weather.gov/points/{lat},{lon}"  # build url
    response = requests.get(url, headers=HEADERS, timeout=30)  # location metadata
    response.raise_for_status()
    data = response.json()

    if "properties" not in data:
        print("Unexpected Response:")
        print(data)
        raise ValueError("No properties field found in NWS response")

    return data["properties"]["forecastHourly"]  # extract hourly forecast


def get_hourly_weather(county):
    '''
    get hourly forecast data per county
    '''
    forecast_url = get_forecastURL(county["lat"], county["lon"])  # get hourly forecast url
    response = requests.get(forecast_url, headers=HEADERS, timeout=30)  # actual forecast
    response.raise_for_status()

    periods = response.json()["properties"]["periods"]  # hourly forecast periods

    # iterate through each period
    rows = []
    for p in periods:
        rows.append({
            "county": county["county"],
            "state": county["state"],
            "county_fips": county["fips"],
            "timestamp": p.get("startTime"),
            "temperature_f": p.get("temperature"),
            "wind_speed_raw": p.get("windSpeed"),
            "short_forecast": p.get("shortForecast"),
        })

    return rows


def ingest():
    all_rows = []

    for county in COUNTIES:
        try:
            rows = get_hourly_weather(county)
            all_rows.extend(rows)
        except Exception as e:
            print(f"Failed for {county['county']}: {e}")

    df = pd.DataFrame(all_rows)
    df.to_csv(HOURLY_CSV, index=False)
    print(df["county"].value_counts())


# ---------------------------------------------------------------------------
# Clean: convert text fields to numeric and aggregate hourly -> daily
# ---------------------------------------------------------------------------

def parse_wind_speed(value):
    if pd.isna(value):
        return None

    nums = re.findall(r"\d+", str(value))

    if len(nums) == 0:
        return None

    nums = [int(n) for n in nums]

    if len(nums) == 1:
        return nums[0]

    return sum(nums) / len(nums)


def clean():
    df = pd.read_csv(HOURLY_CSV)

    # wind speed
    df["wind_mph"] = df["wind_speed_raw"].apply(parse_wind_speed)

    # make numeric columns safer
    df["temperature_f"] = pd.to_numeric(df["temperature_f"], errors="coerce")
    df["wind_mph"] = pd.to_numeric(df["wind_mph"], errors="coerce")

    # date time stuff
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["date"] = df["timestamp"].dt.date

    # groupby to go from hourly weather to daily
    weather_daily = (
        df.groupby(["county_fips", "county", "state", "date"], as_index=False)
          .agg(
              avg_temp_f=("temperature_f", "mean"),
              max_temp_f=("temperature_f", "max"),
              avg_wind_mph=("wind_mph", "mean"),
              max_wind_mph=("wind_mph", "max"),
          )
    )

    weather_daily.to_csv(CLEAN_CSV, index=False)


# ---------------------------------------------------------------------------
# Historical: daily weather 2015-2025 from the Open-Meteo archive
# ---------------------------------------------------------------------------

def fetch_historical_year(county, year, max_retries=5):
    '''
    get one year of daily weather for one county
    '''
    params = {
        "latitude": county["lat"],
        "longitude": county["lon"],
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "daily": ",".join(HISTORICAL_DAILY_VARS),
        "hourly": ",".join(HISTORICAL_HOURLY_VARS),
        "timezone": "America/Los_Angeles",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
    }

    for attempt in range(max_retries):
        response = requests.get(ARCHIVE_URL, params=params, timeout=60)

        if response.status_code == 429:  # rate limited -> back off and retry
            wait = 2 ** attempt * 5
            print(f"  rate limited, waiting {wait}s")
            time.sleep(wait)
            continue

        response.raise_for_status()
        data = response.json()
        break
    else:
        raise RuntimeError("too many retries (rate limited)")

    # daily variables
    daily = pd.DataFrame(data["daily"])
    daily["date"] = pd.to_datetime(daily["time"]).dt.date
    daily = daily.drop(columns="time")

    # hourly humidity -> daily minimum
    hourly = pd.DataFrame(data["hourly"])
    hourly["date"] = pd.to_datetime(hourly["time"]).dt.date
    humidity = (
        hourly.groupby("date", as_index=False)
              .agg(min_humidity=("relative_humidity_2m", "min"))
    )

    df = daily.merge(humidity, on="date", how="left")
    df.insert(0, "date", df.pop("date"))  # move date to the front

    df.insert(0, "state", county["state"])
    df.insert(0, "county", county["county"])
    df.insert(0, "county_fips", county["fips"])

    return df


def ingest_historical():
    frames = []

    for county in COUNTIES:
        for year in range(START_YEAR, END_YEAR + 1):
            try:
                print(f"{county['county']} {year}")
                frames.append(fetch_historical_year(county, year))
            except Exception as e:
                print(f"Failed for {county['county']} {year}: {e}")
            time.sleep(1)  # be polite to the free API

    weather = pd.concat(frames, ignore_index=True)

    weather = weather.rename(columns={
        "temperature_2m_max": "max_temp_f",
        "wind_speed_10m_max": "max_wind_mph",
        "wind_gusts_10m_max": "max_gust_mph",
        "precipitation_sum": "precip_in",
    })

    weather = weather.sort_values(["county", "date"]).reset_index(drop=True)
    weather.to_csv(HISTORICAL_CSV, index=False)

    print(weather.shape)
    print(weather["county"].value_counts())
    print(weather.isna().sum())


def main():
    ingest()             # NWS hourly forecast -> weather_hourly.csv
    clean()              # hourly -> daily     -> weather_clean.csv
    ingest_historical()  # 2015-2025 history   -> weather_historical.csv (takes a few minutes)


if __name__ == "__main__":
    main()