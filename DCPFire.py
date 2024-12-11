import pandas as pd
import numpy as np
import geopandas as gpd
from DCPConstants import DCPConstants


class DCPFire:
    def __init__(self, province, year, months):
        self.province_code=DCPConstants.PROVINCE_CODES[province]
        self.year=int(year)
        self.months=[int(DCPConstants.MONTHS_DICT[month]) for month in months]
        self.directory = province.replace(" ", "_")

    def generate_provincial_shp(self, filename):
        ca_fire_gdf=gpd.read_file(filename)
        provincial_gdf = ca_fire_gdf[ca_fire_gdf['SRC_AGENCY'] == self.province_code]
        data = provincial_gdf.copy()
        data.to_file(f'{self.directory}/FireData.shp')

    def generate_dataset(self):
        grid_layer = gpd.read_file(f'{self.directory}/clippedGrid.shp')
        fire_gdf = gpd.read_file(f'{self.directory}/FireData.shp')

        # Ensure both layers have the same CRS
        if grid_layer.crs != fire_gdf.crs:
            fire_gdf = fire_gdf.to_crs(grid_layer.crs)

        # Join attributes by location
        joined = gpd.sjoin(grid_layer, fire_gdf, how="left", predicate="intersects")

        # Create 'date' column conditionally
        joined['REP_DATE'] = pd.to_datetime(joined['REP_DATE'], errors='coerce')
        joined['date'] = pd.to_datetime(joined[['YEAR', 'MONTH', 'DAY']], errors='coerce')

        # If YEAR, MONTH, or DAY is null, use REP_DATE for 'date'
        joined['date'] = joined['date'].fillna(joined['REP_DATE'])

        # Filter the DataFrame
        joined = joined[(joined['date'].dt.month.isin(self.months)) & (joined['date'].dt.year == self.year)]

        joined.drop(columns=[col for col in joined.columns if col not in ['id', 'date']], inplace=True)
        joined.rename(columns={'id': 'Grid_id'}, inplace=True)

        # Fill the ignition columns with an non nan date with 1, and the rest with 0
        joined['ignition'] = np.where(joined['date'].notna(), 1, 0)
        joined.drop_duplicates(inplace=True)

        return joined
