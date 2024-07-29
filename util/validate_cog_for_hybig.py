import rioxarray
import argparse

def validate_cog(file_path):
    try:
        # Open the COG file using rioxarray
        dataset = rioxarray.open_rasterio(file_path)

        # Check if CRS is defined
        if dataset.rio.crs is None:
            print(f"COG file {file_path} does not have a defined CRS.")
            return False

        # Check the number of bands
        num_bands = dataset.rio.count
        if num_bands not in [1, 3, 4]:
            print(f"COG file {file_path} has {num_bands} bands. Expected 1, 3, or 4 bands.")
            return False

        print(f"COG file {file_path} is valid.")
        return True

    except Exception as e:
        print(f"Error validating COG file {file_path}: {e}")
        return False

if __name__ == "__main__":
    # Define command line arguments
    parser = argparse.ArgumentParser(description="Validate a Cloud-Optimized GeoTIFF (COG) file for HyBIG service requirements.")
    parser.add_argument('file', type=str, help="Path to the COG file")

    # Parse command line arguments
    args = parser.parse_args()

    # Call the validation function
    validate_cog(args.file)

