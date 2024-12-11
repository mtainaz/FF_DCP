from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
import rasterio
from rasterio.warp import calculate_default_transform
import numpy as np
import pandas as pd
import geopandas as gpd
from rasterio.mask import mask
import rasterstats as rs
from dotenv import load_dotenv
import os
from DCPConstants import DCPConstants


class DCPTopographical:
    def __init__(self, province, features):
        self.province = province
        self.features = features
        self.directory = self.province.replace(" ", "_")

    def generate_dataset(self):
        self.image_file=f'{self.directory}/output_image.tif'
        if not os.path.exists(self.image_file):
            self.generate_dem()

        self.elev_output_path= f'{self.directory}/DEM.tif'
        if not os.path.exists(self.elev_output_path):
            self.clip_dem()

        if {"Slope", "Aspect"} & set(self.features):
            self.slope_output_path = f'{self.directory}/slope.tif'
            self.aspect_output_path = f'{self.directory}/aspect.tif'
            self.slope_aspect()

        # Load the centroids shapefile
        clipped_grid_path = f'{self.directory}/clippedGrid.shp'
        clipped_grid = gpd.read_file(clipped_grid_path)

        # Create a new DataFrame to store the mean values for slope, aspect, and elevation
        zonal_means = clipped_grid[["id"]].copy()
        zonal_means.rename(columns={'id':'Grid_id'}, inplace=True)

        if "Elevation" in self.features:
            # Calculate the elevation values
            elevation_stats = rs.zonal_stats(
                clipped_grid_path,
                self.elev_output_path,
                stats=['mean'],
                band=1
            )

            # Convert the statistics into a DataFrame and add it to zonal_means
            zonal_means["elevation"] = pd.DataFrame(elevation_stats)["mean"]

        if "Slope" in self.features:
            # Extract the slope values for each Grid_id using zonal statistics
            slope_stats = rs.zonal_stats(
                clipped_grid_path,
                self.slope_output_path,
                stats=['mean'],
                band=1
            )

            # Convert the statistics into a DataFrame and add it to zonal_means
            zonal_means["slope"] = pd.DataFrame(slope_stats)["mean"]

        if "Aspect" in self.features:
            # Extract the aspect values for each Grid_id using zonal statistics
            aspect_stats = rs.zonal_stats(
                clipped_grid_path,
                self.aspect_output_path,
                stats=['mean'],
                band=1
            )

            # Convert the statistics into a DataFrame and add it to zonal_means
            zonal_means["aspect"] = pd.DataFrame(aspect_stats)["mean"]
            # zonal_means.dropna(inplace=True)  # Drop any row with NaN values
        return zonal_means


    def generate_dem(self):
        load_dotenv()
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        bbox_data = DCPConstants.PROVINCE_DICT[self.province]
        bbox = [bbox_data[1], bbox_data[2], bbox_data[3], bbox_data[0]]  # [West, South, East, North]

        # Create an OAuth2 session
        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)

        # Calculate the spatial extent in meters (approx.)
        lon_diff = bbox[2] - bbox[0]  # East - West
        lat_diff = bbox[3] - bbox[1]  # North - South
        meters_per_degree_lon = 111_320  # Approx. meters per degree longitude
        meters_per_degree_lat = 110_574  # Approx. meters per degree latitude
        width_meters = lon_diff * meters_per_degree_lon
        height_meters = lat_diff * meters_per_degree_lat

        # Set the desired resolution (in meters per pixel) and calculate dimensions
        desired_resolution_meters = DCPConstants.RESOLUTION  # Max 1500 meters per pixel allowed
        width_pixels = int(width_meters / desired_resolution_meters)
        height_pixels = int(height_meters / desired_resolution_meters)

        # Step 1: Cap the width and height to the API's limits
        MAX_PIXELS = 2500
        if width_pixels > MAX_PIXELS:
            width_pixels = MAX_PIXELS

        if height_pixels > MAX_PIXELS:
            height_pixels = MAX_PIXELS

        # Fetch the OAuth2 access token
        try:
            token = oauth.fetch_token(
                token_url='https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
                client_id=client_id,
                client_secret=client_secret,
                include_client_id=True
            )
        except Exception as e:
            print(f"Error fetching token: {e}")
            return

        # Step 2: Fetch the access token
        if token is None:
            exit("Failed to obtain access token.")

        # Step 3: Test the API connection
        try:
            response = oauth.get("https://sh.dataspace.copernicus.eu/configuration/v1/wms/instances")
            if response.status_code == 200:
                print("WMS Instances:", response.content)
            else:
                print(f"Error fetching WMS instances: {response.status_code} - {response.content}")
        except Exception as e:
            print(f"Error during API request: {e}")
            return

        # Step 4: Define the evalscript to process DEM data
        evalscript = """
        //VERSION=3
        function setup() {
          return {
            input: ["DEM"],
            output: { bands: 1 },
          }
        }

        function evaluatePixel(sample) {
          return [sample.DEM / 1000]; // Convert elevation from meters to kilometers
        }
        """

        # Step 5: Define the POST request payload
        request = {
            "input": {
                "bounds": {
                    "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
                    "bbox": bbox,
                },
                "data": [
                    {
                        "type": "dem",
                        "dataFilter": {"demInstance": "COPERNICUS_30"},
                        "processing": {
                            "upsampling": "BILINEAR",
                            "downsampling": "BILINEAR",
                        },
                    }
                ],
            },
            "output": {
                "width": width_pixels,
                "height": height_pixels,
                "responses": [
                    {
                        "identifier": "default",
                        "format": {"type": "image/tiff"},
                    }
                ],
            },
            "evalscript": evalscript,
        }

        # Step 6: Send the POST request to process DEM data
        url = "https://sh.dataspace.copernicus.eu/api/v1/process"
        try:
            response = oauth.post(url, json=request)
            if response.status_code == 200:
                # Save the processed image to a file
                with open(f'{self.image_file}', 'wb') as f:
                    f.write(response.content)
                print("DEM processing successful, image saved as 'output_image.png'")
            else:
                print(f"Error in DEM processing: {response.status_code} - {response.content}")
                return
        except Exception as e:
            print(f"Error during DEM processing request: {e}")
            return
        return

    # Function to calculate slope
    def calculate_slope(self, dem, pixel_size):
        # Calculate the gradient in the x and y directions
        dx, dy = np.gradient(dem, pixel_size[0], pixel_size[1])

        # Compute the slope using arctangent of the square root of the sum of squares
        slope = np.arctan(np.sqrt(dx ** 2 + dy ** 2)) * 180 / np.pi

        return slope

    # Function to calculate aspect from DEM
    def calculate_aspect(self, dem, pixel_size):
        # Compute the gradient in x and y directions
        dx, dy = np.gradient(dem, pixel_size[0], pixel_size[1])

        # Calculate the aspect in degrees
        aspect = np.degrees(np.arctan2(dx, -dy))

        # Ensure aspect values are within the 0-360 range
        aspect = (aspect + 360) % 360

        return aspect

    def clip_dem(self):
        shp_file_path=f'{self.directory}/Province.shp'
        input_layer = gpd.read_file(shp_file_path)
        target_crs = input_layer.crs

        with rasterio.open(self.image_file) as src:
            transform, width, height = rasterio.warp.calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': target_crs,
                'transform': transform,
                'width': width,
                'height': height
            })

            output_reprojected_path = f"{self.directory}/Reprojected.tif"
            with rasterio.open(output_reprojected_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    rasterio.warp.reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=rasterio.enums.Resampling.nearest
                    )

        # Convert the grid to a GeoJSON-like format
        geoms = [feature["geometry"] for feature in input_layer.__geo_interface__["features"]]

        output_reprojected_data = rasterio.open(output_reprojected_path)

        # Clip the reprojected raster using the grid geometry
        out_image, out_transform = mask(output_reprojected_data, geoms, crop=True)
        out_meta = output_reprojected_data.meta.copy()

        # Update metadata for the clipped image
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })

        # Save the clipped raster
        with rasterio.open(self.elev_output_path, "w", **out_meta) as dest:
            dest.write(out_image)

    def slope_aspect(self):
        # Open the DEM file using rasterio
        with rasterio.open(self.elev_output_path) as dem_dataset:
            dem = dem_dataset.read(1)  # Read the first band

            # Get the pixel size (resolution) from the DEM's metadata
            dx = dem_dataset.transform[0]  # Pixel width
            dy = -dem_dataset.transform[4]  # Pixel height (negative because y-coordinates increase downward)

            # Calculate the slope and create tif file
            if "Slope" in self.features and not os.path.exists(self.slope_output_path):
                slope = self.calculate_slope(dem, (dx, dy))
                with rasterio.open(
                        self.slope_output_path,
                        'w',
                        driver='GTiff',
                        height=slope.shape[0],
                        width=slope.shape[1],
                        count=1,
                        dtype=slope.dtype,
                        crs=dem_dataset.crs,
                        transform=dem_dataset.transform,
                ) as slope_dataset:
                    slope_dataset.write(slope, 1)

            # Calculate the aspect and create tif
            if "Aspect" in self.features and not os.path.exists(self.aspect_output_path):
                aspect = self.calculate_aspect(dem, (dx, dy))
                with rasterio.open(
                        self.aspect_output_path,
                        'w',
                        driver='GTiff',
                        height=aspect.shape[0],
                        width=aspect.shape[1],
                        count=1,
                        dtype='float32',  # Use float32 for aspect values
                        crs=dem_dataset.crs,
                        transform=dem_dataset.transform,
                ) as aspect_dataset:
                    aspect_dataset.write(aspect, 1)
        return

if __name__ == "__main__":
    cop = DCPTopographical("British Columbia", ["Slope", "Aspect", "Elevation"])
    cop_df=cop.generate_dataset()
