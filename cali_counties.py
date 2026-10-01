import csv

'''
Defines 10 coastal California counties 

writes to csv file 
'''

COUNTIES = [
    {
        "county": "San Francisco",
        "state": "CA",
        "fips": "06075",
        "lat": 37.7749,
        "lon": -122.4194,
    },
    {
        "county": "San Mateo",
        "state": "CA",
        "fips": "06081",
        "lat": 37.5630,
        "lon": -122.3255,
    },
    {
        "county": "Santa Cruz",
        "state": "CA",
        "fips": "06087",
        "lat": 36.9741,
        "lon": -122.0308,
    },
    {
        "county": "San Luis Obispo",
        "state": "CA",
        "fips": "06079",
        "lat": 35.2828,
        "lon": -120.6596,
    },
    {
        "county": "Monterey",
        "state": "CA",
        "fips": "06053",
        "lat": 36.6002,
        "lon": -121.8947,
    },
    {
        "county": "Santa Barbara",
        "state": "CA",
        "fips": "06083",
        "lat": 34.4208,
        "lon": -119.6982,
    },
    {
        "county": "Ventura",
        "state": "CA",
        "fips": "06111",
        "lat": 34.2805,
        "lon": -119.2945,
    },
    {
        "county": "Los Angeles",
        "state": "CA",
        "fips": "06037",
        "lat": 34.0522,
        "lon": -118.2437,
    },
    {
        "county": "Orange",
        "state": "CA",
        "fips": "06059",
        "lat": 33.7175,
        "lon": -117.8311,
    },
    {
        "county": "San Diego",
        "state": "CA",
        "fips": "06073",
        "lat": 32.7157,
        "lon": -117.1611,
    },
]

FIELDNAMES = ["county", "state", "fips", "lat", "lon"]

with open("counties.csv", "w") as csvfile: 
    writer = csv.DictWriter(csvfile, fieldnames = FIELDNAMES)
    writer.writeheader() 
    writer.writerows(COUNTIES)