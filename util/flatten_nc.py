import os
import sys
import xarray as xr
import argparse

# Run this utility program from the command line:
# python flatten_nc.py -f path/to/your/file.nc -g group1,group2,group3
# Example: python flatten_nc.py -f /Users/srizvi/data/TEMPO_CLDO4_L2_V02_20230802T151249Z_S001G01.nc -g geolocation,product,qa_statistics,support_data

def flatten_nc_file(file_path, groups=None):
    if file_path.endswith(".nc"):
        # Construct the output file name with '_flattened' before the .nc extension
        output_name = os.path.splitext(file_path)[0] + "_flattened.nc"

        # Open the main dataset
        ds0 = xr.open_dataset(file_path)

        # If no groups specified, flatten all groups if they exist
        if groups is None:
            groups = list(ds0.groups.keys()) if ds0.groups else []
        
        # Check for existing groups and update the main dataset
        for gn in groups:
            try:
                # Check if the group exists
                with xr.open_dataset(file_path, group=gn) as ds:
                    ds0.update(ds)
            except OSError:
                # Group does not exist, skip it
                continue

        # Save the flattened dataset
        ds0.to_netcdf(output_name)
        print(f"Flattened file saved as: {output_name}")

        # Return the path of the flattened file
        return output_name

    else:
        print("The provided file is not a .nc file.")
        return None

if __name__ == "__main__":
    # Define command line arguments
    parser = argparse.ArgumentParser(description="Flatten a NetCDF file by merging specific groups.")
    parser.add_argument('-f', '--file', type=str, required=True, help="Path to the .nc file")
    parser.add_argument('-g', '--groups', type=str, help="Comma-separated list of groups to merge into the main dataset")
    
    # Parse command line arguments
    args = parser.parse_args()

    # Call the function to flatten the .nc file
    flattened_file = flatten_nc_file(args.file, groups=args.groups.split(',') if args.groups else None)
    
    # Check if a flattened file was created and print its path
    if flattened_file:
        print(f"Flattened file path: {flattened_file}")
