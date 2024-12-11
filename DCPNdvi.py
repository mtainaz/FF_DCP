import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime, timedelta
from sentinelhub import (
    SHConfig,
    DataCollection,
    SentinelHubRequest,
    BBox,
    CRS,
    MimeType
)
from dotenv import load_dotenv
import os
from DCPConstants import DCPConstants
from DCPHelper import DCPHelper

class DCPNdvi:
    def __init__(self, province, year, months):
        self.province=province
        self.year=int(year)
        self.months=[int(DCPConstants.MONTHS_DICT[month]) for month in months]
        self.directory = self.province.replace(" ", "_")

    def generate_dataset(self):
        self.create_config_params()
        self.generate_dates()
        all_df=[]
        col=1
        for week in self.weeks:
            col_name = f'NDVI_{col}'
            start=str(week[0].date())
            end=str(week[-1].date())
            week_df=self.create_weekly_ndvi(start,end,col_name)
            all_df.append(week_df)
            col+=1

        # Merge all datasets on grid_id
        self.merged_df=DCPHelper.merge_grid_id('inner', all_df)
        out_df=self.create_daily_data()
        return out_df

    def create_config_params(self):
        self.grid_layer = gpd.read_file(f'{self.directory}/clippedGrid.shp')
        load_dotenv()
        self.config = SHConfig()
        self.config.sh_client_id = os.getenv("CLIENT_ID")
        self.config.sh_client_secret = os.getenv("CLIENT_SECRET")
        self.config.sh_base_url = 'https://sh.dataspace.copernicus.eu'
        self.config.sh_token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'

        bbox_data = DCPConstants.PROVINCE_DICT[self.province]
        self.bbox = (bbox_data[1], bbox_data[2], bbox_data[3], bbox_data[0])  # [West, South, East, North]
        self.aoi_bbox = BBox(bbox=self.bbox, crs=CRS.WGS84)

        # Calculate bounding box dimensions in meters
        lon_diff = self.bbox[2] - self.bbox[0]  # East - West
        lat_diff = self.bbox[3] - self.bbox[1]  # North - South

        # Approximate meters per degree (average values)
        meters_per_degree_lon = 111_320  # Approx. meters per degree longitude
        meters_per_degree_lat = 110_574  # Approx. meters per degree latitude

        # Calculate width and height in meters
        width_meters = lon_diff * meters_per_degree_lon
        height_meters = lat_diff * meters_per_degree_lat

        # Desired resolution in meters per pixel (e.g., 1000 meters per pixel)
        desired_resolution_meters = DCPConstants.RESOLUTION  # Max 1500 meters per pixel allowed

        # Calculate the image dimensions in pixels
        self.width_pixels = int(width_meters / desired_resolution_meters)
        self.height_pixels = int(height_meters / desired_resolution_meters)

        # Cap the width and height to the API's limits
        MAX_PIXELS = 2500
        if self.width_pixels > MAX_PIXELS:
            self.width_pixels = MAX_PIXELS

        if self.height_pixels > MAX_PIXELS:
            self.height_pixels = MAX_PIXELS

        self.aoi_size = (self.width_pixels, self.height_pixels)

    def generate_dates(self):
        dates = []
        for month in self.months:
            date = datetime(self.year, month, 1)
            while date.month == month:
                dates.append(date)
                date += timedelta(days=1)

        # Divide the dates into weeks
        self.weeks = []
        k = 0
        for i in range(len(dates)):
            if i > 0 and (dates[i] - self.weeks[k][0]).days < 7:
                self.weeks[k].append(dates[i])
            else:
                self.weeks.append([dates[i]])
                if i == 0:
                    continue
                k += 1

    def create_weekly_ndvi(self, start_date, end_date, col_name):
        evalscript_ndvi = """
        //VERSION=3
        function setup() {
          return {
            input: [
              {
                bands: ["B04", "B08"],
                units: "REFLECTANCE",
              },
            ],
            output: {
              id: "default",
              bands: 1,
              sampleType: SampleType.FLOAT32,
            },
          }
        }


        function evaluatePixel(sample) {
            let val = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
            return [val]
        }

        """

        request_ndvi_img = SentinelHubRequest(
            evalscript=evalscript_ndvi,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A.define_from(
                        name="s2l2a", service_url="https://sh.dataspace.copernicus.eu"
                    ),
                    time_interval=(start_date, end_date),
                    other_args={"dataFilter": {"mosaickingOrder": "leastCC"}},
                )
            ],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=self.aoi_bbox,
            size=self.aoi_size,
            config=self.config,
        )

        ndvi_img = request_ndvi_img.get_data()

        ndvi_array = ndvi_img[0]

        # Prepare latitude and longitude grid corresponding to the image size
        latitudes = np.linspace(self.bbox[1], self.bbox[3], self.height_pixels)
        longitudes = np.linspace(self.bbox[0], self.bbox[2], self.width_pixels)

        # Create a mesh grid of latitudes and longitudes
        lat_grid, lon_grid = np.meshgrid(latitudes, longitudes, indexing="ij")

        # Flatten the grids and NDVI array for vectorized DataFrame creation
        lat_flat = lat_grid.flatten()
        lon_flat = lon_grid.flatten()
        ndvi_flat = ndvi_array.flatten()

        # Combine into a DataFrame
        lat_long_df = pd.DataFrame({
            "Latitude": lat_flat,
            "Longitude": lon_flat,
            col_name: ndvi_flat
        })

        geometry = [Point(xy) for xy in zip(lat_long_df['Longitude'], lat_long_df['Latitude'])]
        ndvi_gdf = gpd.GeoDataFrame(lat_long_df, geometry=geometry, crs="EPSG:4326")

        # Ensure both layers have the same CRS
        ndvi_gdf = ndvi_gdf.to_crs(self.grid_layer.crs)

        # Perform spatial join to get the ID from the shapefile
        joined = gpd.sjoin(self.grid_layer, ndvi_gdf, how="left", predicate="intersects")
        results = joined.drop(columns=['geometry', 'index_right', 'Latitude', 'Longitude'])

        # Get the mean NDVI for each Grid_id
        out_df = results.groupby('id', as_index=False)[col_name].mean().rename(columns={'id': 'Grid_id'})
        return out_df

    def create_daily_data(self):
        data = []
        # Assign dates to NDVI rows
        for _, row in self.merged_df.iterrows():
            col = 1
            for week in self.weeks:
                col_name = f'NDVI_{col}'
                for day in week:
                    new_row = {'Grid_id': row['Grid_id'], 'date': day, 'NDVI': row[col_name]}
                    data.append(new_row)
                col += 1

        out_df = pd.DataFrame(data)
        return out_df

if __name__ == "__main__":
    ndvi = DCPNdvi("British Columbia", "2017", ['January', 'February'])
    ndvi_df=ndvi.generate_dataset()

