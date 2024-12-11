class DCPConstants:
    PROVINCE_DICT = {
        "Alberta": [60.0, -120.0, 49.0, -110.0], #[North, West, South, East]
        "British Columbia": [60.01, -139.04, 48.25, -114.08],
        "Manitoba": [60.0, -102.0, 49.0, -94.0],
        "New Brunswick": [48.5, -66.5, 45.5, -63.0],
        "Newfoundland and Labrador": [61.0, -64.0, 46.0, -52.0],
        "Nova Scotia": [48.5, -66.0, 43.5, -60.0],
        "Ontario": [57.0, -95.0, 41.7, -74.0],
        "Quebec": [62.0, -80.0, 44.0, -57.5],
        "Saskatchewan": [60.0, -110.0, 49.0, -101.0]
    }

    PROVINCE_CODES = {
        "Alberta": "AB",
        "British Columbia": "BC",
        "Manitoba": "MB",
        "New Brunswick": "NB",
        "Newfoundland and Labrador": "NL",
        "Nova Scotia": "NS",
        "Ontario": "ON",
        "Quebec": "QC",
        "Saskatchewan": "SK"
    }

    GRID_SIZE=(10000, 10000) #In meters

    RESOLUTION=1000 #In meters per pixel, max 1500 meters per pixel allowed (For NDVI and DEM)

    MONTHS_DICT={"January":"01",
                 "February":"02",
                 "March":"03",
                 "April":"04",
                 "May":"05",
                 "June":"06",
                 "July":"07",
                 "August":"08",
                 "September":"09",
                 "October": "10",
                 "November": "11",
                 "December": "12"}

    FEATURES_LIST=["Temperature", "Total Precipitation", "Average Wind Speed", "Relative Humidity",
                   "Slope", "Aspect", "Elevation", "NDVI"]