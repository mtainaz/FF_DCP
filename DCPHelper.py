import os
import pandas as pd

class DCPHelper:
    def getFilenameNoPath(filename: str):
        return os.path.basename(filename)

    def merge(merge_type: str, *args):
        # If a list of DataFrames is passed instead of individual arguments, unpack it
        if len(args) == 1 and isinstance(args[0], list):
            args = args[0]

        # Start merging from the first DataFrame in the list
        merged_data = args[0]
        for file_data in args[1:]:
            merged_data = merged_data.merge(file_data, how=merge_type, on=['Grid_id', 'date'])

        return merged_data

    def merge_grid_id(merge_type: str, *args):
        # If a list of DataFrames is passed instead of individual arguments, unpack it
        if len(args) == 1 and isinstance(args[0], list):
            args = args[0]

        # Start merging from the first DataFrame in the list
        merged_data = args[0]
        for file_data in args[1:]:
            merged_data = merged_data.merge(file_data, how=merge_type, on=['Grid_id'])

        return merged_data


