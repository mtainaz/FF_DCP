import os
import geopandas as gpd
import math
from shapely.geometry import Polygon
from DCPConstants import DCPConstants

class DCPShpGenerator:
    def __init__(self, province: str, selected_file: str):
        self.province=province
        self.selected_file=selected_file
        self.directory=self.province.replace(" ", "_")
        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

    def create_provincial_grid(self):
        output_file=f"{self.directory}/Province.shp"
        if not os.path.exists(output_file):
            canada_gdf = gpd.read_file(self.selected_file)
            data=canada_gdf[canada_gdf['PRENAME']==self.province]
            provincial_gdf=data.copy()
            provincial_gdf.to_file(output_file) # Save the provincial shp file

            # Get the bounding box of the dataset
            minx, miny, maxx, maxy = provincial_gdf.total_bounds
            horizontal_spacing, vertical_spacing = DCPConstants.GRID_SIZE

            # Create the grid GeoDataFrame
            polygons = []

            for x in range(int(math.floor(minx)), int(math.ceil(maxx)), horizontal_spacing):
                for y in range(int(math.floor(miny)), int(math.ceil(maxy)), vertical_spacing):
                    cell = Polygon([(x, y), (x + horizontal_spacing, y),
                                    (x + horizontal_spacing, y + vertical_spacing),
                                    (x, y + vertical_spacing)])
                    polygons.append(cell)

            # Create a GeoDataFrame from the list of polygons
            grid = gpd.GeoDataFrame(geometry=polygons, crs=provincial_gdf.crs)
            self.clipped_grid = gpd.clip(grid, provincial_gdf)
            self.clipped_grid['id'] = self.clipped_grid.index
            self.clipped_grid.to_file(f"{self.directory}/clippedGrid.shp")
        return

    def create_provincial_centroids(self):
        output_centroids_path=f"{self.directory}/centroids.shp"
        if not os.path.exists(output_centroids_path):
            centroids_gdf = gpd.GeoDataFrame({'id': self.clipped_grid['id'], 'geometry': self.clipped_grid.geometry.centroid})
            centroids_gdf.to_file(output_centroids_path)
        return

if __name__ == "__main__":
    shp = DCPShpGenerator("British Columbia", 'C:/Users/taina/Dropbox/PC/Downloads/lpr_000b21a_e/lpr_000b21a_e.shp')
    shp.create_provincial_grid()
    shp.create_provincial_centroids()
