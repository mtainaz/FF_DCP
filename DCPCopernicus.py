import os.path
import cdsapi
import geopandas as gpd
import rasterio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from rasterio.warp import calculate_default_transform, reproject, Resampling
from DCPConstants import DCPConstants
from DCPHelper import DCPHelper

class DCPCopernicus:
    def __init__(self, province, year, months, features):
        self.province=province
        self.year=year
        self.months=[DCPConstants.MONTHS_DICT[month] for month in months]
        self.features=features
        self.directory = self.province.replace(" ", "_")

    def generate_dataset(self):
        all_df=[]
        temp_df=pd.DataFrame()
        if "Temperature" in self.features:
            self.generate_grib('2m_temperature')
            self.reproject_raster()
            temp_df=self.sample_data('T')
            all_df.append(temp_df)

        if "Total Precipitation" in self.features:
            self.generate_grib('total_precipitation')
            self.reproject_raster()
            prcp_df=self.sample_data('Prcp')
            all_df.append(prcp_df)

        if "Average Wind Speed" in self.features:
            # Generate the u component of wind values
            self.generate_grib('10m_u_component_of_wind')
            self.reproject_raster()
            unorm_df=self.sample_data('unorm')

            # Generate the v component of wind values
            self.generate_grib('10m_v_component_of_wind')
            self.reproject_raster()
            vnorm_df=self.sample_data('vnorm')

            # Merge the 2 dataframes and calculate average wind speed
            ws_df=DCPHelper.merge('inner',unorm_df,vnorm_df)
            ws_df['Ws']=np.sqrt(ws_df['unorm']**2 + ws_df['vnorm']**2)
            ws_df = ws_df.drop(columns=['unorm', 'vnorm'])
            all_df.append(ws_df)

        if "Relative Humidity" in self.features:
            if temp_df.empty:
                self.generate_grib('2m_temperature')
                self.reproject_raster()
                temp_df = self.sample_data('T')
            self.generate_grib('2m_dewpoint_temperature')
            self.reproject_raster()
            dew_temp_df = self.sample_data('dew')
            rel_hum_df = DCPHelper.merge('inner', temp_df, dew_temp_df) # Combine temperature and dewpoint temperature

            # Calculate saturation vapor pressure at temperature and dewpoint temperature
            # Note: Temperatures need to be converted to Celsius
            es_dew_temp = np.exp(17.625 * (rel_hum_df['dew'] - 273.15) / (rel_hum_df['dew'] - 30.11))
            es_temp = np.exp(17.625 * (rel_hum_df['T'] - 273.15) / (rel_hum_df['T'] - 30.11))

            # Calculate Relative Humidity
            rel_hum_df['RelHum'] = (es_dew_temp / es_temp) * 100
            rel_hum_df=rel_hum_df.drop(columns=['dew','T'])
            all_df.append(rel_hum_df)

        merged_df=DCPHelper.merge('outer',all_df) #merge all resulting dataframes
        return merged_df

    def generate_grib(self, variable):
        client = cdsapi.Client()
        dataset = "reanalysis-era5-single-levels"
        request_params = {
            'product_type': 'reanalysis',
            'variable': variable,
            'year': self.year,
            'month': self.months,  # List of months
            'day': [f"{i:02}" for i in range(1, 32)],  # All days in each month
            'time': '12:00',
            'format': 'grib',
            'area': DCPConstants.PROVINCE_DICT[self.province]
        }

        target_path=f"{self.directory}/Dataset.grib"
        # Delete the previous grib file (if it exists)
        if os.path.exists(target_path):
            os.remove(target_path)

        client.retrieve(dataset, request_params, target_path)

    def reproject_raster(self):
        input_layer=gpd.read_file(f"{self.directory}/Province.shp")
        cop_data_path=f"{self.directory}/Dataset.grib"

        target_crs = input_layer.crs

        # Open the source raster
        with rasterio.open(cop_data_path) as src:
            # Calculate the transform, width, and height to reproject the raster to the target CRS
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )

            # Update the metadata for the output raster
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': target_crs,  # Explicitly set target CRS
                'transform': transform,
                'width': width,
                'height': height
            })

            # Define the path for the reprojected raster
            self.reprojected_raster_path = f"{self.directory}/cop_reprojected.tif"

            # Delete the previous reprojected raster (if it exists)
            if os.path.exists(self.reprojected_raster_path):
                os.remove(self.reprojected_raster_path)

            # Reproject and save the new raster
            with rasterio.open(self.reprojected_raster_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):  # Process each band in the raster
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=Resampling.bilinear  # Use bilinear resampling for continuous data
                    )

    def sample_data(self, prefix):
        rep_data = rasterio.open(self.reprojected_raster_path)
        centroids = gpd.read_file(f"{self.directory}/centroids.shp")
        centroids = centroids.to_crs(rep_data.crs)

        # Create a list of coordinates (x, y) from the centroids GeoDataFrame
        coord_list = [(x, y) for x, y in zip(centroids["geometry"].x, centroids["geometry"].y)]

        # Sample the data at the specified coordinates
        Temp_values = [x for x in rep_data.sample(coord_list)]

        # Prepare a dictionary to store data for all days
        temp_data = {f"{prefix}_{day + 1}": [] for day in range(len(Temp_values[0]))}

        # Populate the dictionary with the values
        for id in Temp_values:
            for day, day_temp in enumerate(id):
                temp_data[f"{prefix}_{day + 1}"].append(day_temp)

        # Convert the dictionary to a DataFrame
        temp_df = pd.DataFrame(temp_data)

        # Concatenate the new data columns to the centroids GeoDataFrame
        centroids = pd.concat([centroids, temp_df], axis=1)

        # Save the updated GeoDataFrame as a separate dataframe
        self.cmet_out1 = centroids.drop(columns=['geometry'])

        dates=[]
        for month in self.months:
            date = datetime(int(self.year), int(month), 1)
            while date.month == int(month):
                dates.append(date)
                date += timedelta(days=1)

        all_rows = []
        for _, row in self.cmet_out1.iterrows():
            day = 1
            for date in dates:
                col = f"{prefix}_{day}"
                new_row = {"Grid_id": row['id'], "date": date, prefix: row[col]}
                all_rows.append(new_row)
                day += 1

        out_df = pd.DataFrame(all_rows)
        return out_df


if __name__ == "__main__":
    cop = DCPCopernicus("British Columbia", "2017", ["January"], ["Temperature"])
    cop.generate_dataset()
