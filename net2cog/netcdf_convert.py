# pylint: disable=unused-import
"""
=========
netcdf-convert.py
=========

Functions related to converting a NetCDF file to other formats.
"""

import os
import pathlib
from logging import Logger
from os.path import join as path_join, basename
from tempfile import TemporaryDirectory
from typing import List

import rasterio
import rioxarray  # noqa
import xarray as xr
from rasterio import CRS
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from rioxarray.exceptions import DimensionError

EXCLUDE_VARS = ['lon', 'lat', 'longitude', 'latitude', 'time']


class Net2CogError(Exception):
    """
    Exception raised when an error occurs while converting a NetCDF file to COG
    """

    def __init__(self, variable_name: str, error_message: str):
        super().__init__(
            f'Variable {variable_name} cannot be converted to tif: {error_message}'
        )


def _rioxr_swapdims(netcdf_xarray):
    netcdf_xarray.coords['y'] = ('lat', netcdf_xarray.lat)
    netcdf_xarray.coords['x'] = ('lon', netcdf_xarray.lon)

    return netcdf_xarray.swap_dims({'lat': 'y', 'lon': 'x'})


# pylint: disable=R0914
def _write_cogtiff(
    output_directory: str,
    nc_xarray: xr.Dataset,
    variable_name: str,
    logger: Logger,
) -> str | None:
    """
    This function converts a variable inside a NetCDF file into a
    cloud optimized geotiff.

    Parameters
    ----------
    output_directory : str
        Path to temporary directory where output GeoTIFFs will be stored before
        being staged in S3.
        example :/home/dockeruser/converter/podaac/netcdf_converter/temp/
            netcdf_converter/
            RSS_smap_SSS_L3_8day_running_2020_037_FNL_v04.0_test
    nc_xarray : xarray.Dataset
        xarray dataset loaded from NetCDF file
    variable_name: str
        Name of the variable within the file to convert.
    logger : logging.Logger
        Python Logger object for emitting log messages.

    Notes
    -----
    - Assumption that 0 is always on the prime meridian/equator.
    - The output name for converted GeoTIFFs is `<variable name>.tif`, with any
      slashes replaced with underscores.
    """

    logger.debug("NetCDF Var: %s", variable_name)

    if variable_name in EXCLUDE_VARS:
        logger.debug(f"Variable {variable_name} is excluded. Will not produce COG")
        return None

    output_basename = f'{variable_name}.tif'.replace('/', '_')
    output_file_name = path_join(output_directory, output_basename)

    with TemporaryDirectory() as tempdir:
        temp_file_name = path_join(tempdir, output_basename)

        try:
            nc_xarray[variable_name].rio.to_raster(temp_file_name)
        except KeyError as error:
            # Occurs when trying to locate a variable that is not in the Dataset
            raise Net2CogError(variable_name, error) from error
        except LookupError as err:
            logger.info("Variable %s cannot be converted to tif: %s", variable_name, err)
            raise Net2CogError(variable_name, err) from err
        except DimensionError as dmerr:
            try:
                logger.info("%s: No x or y xarray dimensions, adding them...", dmerr)
                nc_xarray_tmp = _rioxr_swapdims(nc_xarray)
                nc_xarray_tmp[variable_name].rio.to_raster(temp_file_name)
            except RuntimeError as runerr:
                logger.info("Variable %s cannot be converted to tif: %s", variable_name, runerr)
                raise Net2CogError(variable_name, runerr) from runerr
            except Exception as aerr:  # pylint: disable=broad-except
                logger.info("Variable %s cannot be converted to tif: %s", variable_name, aerr)
                raise Net2CogError(variable_name, aerr) from aerr

        # Option to add additional GDAL config settings
        # config = dict(GDAL_NUM_THREADS="ALL_CPUS", GDAL_TIFF_OVR_BLOCKSIZE="128")
        # with rasterio.Env(**config):

        logger.info("Starting conversion... %s", output_file_name)

        # default CRS setting
        # crs = rasterio.crs.CRS({"init": "epsg:3857"})

        with rasterio.open(temp_file_name, mode='r+') as src_dataset:
            # if src_dst.crs is None:
            #     src_dst.crs = crs
            src_dataset.crs = CRS.from_proj4(proj="+proj=latlong")
            dst_profile = cog_profiles.get("deflate")
            cog_translate(
                src_dataset,
                output_file_name,
                dst_profile,
                use_cog_driver=True
            )

    logger.info("Finished conversion, writing variable: %s", output_file_name)
    logger.info("NetCDF conversion complete. Returning COG generated.")
    return output_file_name


def netcdf_converter(
    input_nc_file: pathlib.Path,
    output_directory: pathlib.Path,
    var_list: list[str],
    logger: Logger,
) -> List[str]:
    """Primary function for beginning NetCDF conversion using rasterio,
    rioxarray and xarray

    Parameters
    ----------
    input_nc_file : pathlib.Path
        Path to  NetCDF file to process
    output_directory : pathlib.Path
        Path to temporary directory into which results will be placed before
        staging in S3.
    var_list : str | None
        List of variable names to be converted to various single band cogs,
        ex: ['gland', 'fland', 'sss_smap']. If this list is empty, it is assumed
        that all variables have been requested.
    logger : logging.Logger
        Python Logger object for emitting log messages.

    Notes
    -----
    Currently uses local file paths, no s3 paths
    """
    logger.info("Input file name: %s", input_nc_file)

    netcdf_file = os.path.abspath(input_nc_file)
    logger.debug('NetCDF Path: %s', netcdf_file)

    if netcdf_file.endswith('.nc'):
        logger.info("Reading %s", basename(netcdf_file))

        xds = xr.open_dataset(netcdf_file)

        # NetCDF must have spatial dimensions
        if (({"lon", "lat"}.issubset(set(xds.dims)))
                or ({"longitude", "latitude"}.issubset(set(xds.dims)))
                or ({"x", "y"}.issubset(set(xds.dims)))):
            # used to invert y axis
            # xds_reversed = xds.reindex(lat=xds.lat[::-1])

            if not var_list:
                # Empty list means "all" variables, so get all variables in
                # the `xarray.Dataset`.
                var_list = list(xds.data_vars.keys())

            output_files = [
                _write_cogtiff(output_directory, xds, variable_name, logger)
                for variable_name in var_list
            ]
            # Remove None returns, e.g., for excluded variables
            return [
                output_file
                for output_file in output_files
                if output_file is not None
            ]

        logger.error("%s: NetCDF file does not contain spatial dimensions such as lat / lon "
                     "or x / y", netcdf_file)
        return []
    logger.info("Not a NetCDF file; Skipped file: %s", netcdf_file)
    return []
