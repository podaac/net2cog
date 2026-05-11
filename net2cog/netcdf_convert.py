# pylint: disable=unused-import
"""
=========
netcdf-convert.py
=========

Functions related to converting a NetCDF file to other formats.
"""

import os
import io
import pathlib
from logging import Logger
from os.path import join as path_join, basename
from tempfile import TemporaryDirectory
import warnings

import rasterio
import rioxarray  # noqa
import xarray as xr
from rasterio import CRS
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from rioxarray.exceptions import (
    DimensionError,
    InvalidDimensionOrder,
    MissingSpatialDimensionError
)
from pyproj.crs import CRS as pyCRS
from pyproj.exceptions import CRSError
from net2cog.utilities import (
    resolve_relative_path,
    Net2CogError,
    reorder_dimensions,
    rename_dimensions,
    is_valid_shape,
    is_valid_dtype,
    is_valid_spatial_dimensions,
    get_value_error_handler,
    construct_variable_path,
    identify_file,
    has_object_dtype_variables,
)

EXCLUDE_VARS = ['lon', 'lat', 'longitude', 'latitude', 'time']


def _rioxr_swapdims(netcdf_xarray):
    netcdf_xarray.coords['y'] = ('lat', netcdf_xarray.lat)
    netcdf_xarray.coords['x'] = ('lon', netcdf_xarray.lon)

    return netcdf_xarray.swap_dims({'lat': 'y', 'lon': 'x'})


# pylint: disable=R0914
def _write_cogtiff(
    output_directory: str,
    nc_xarray: xr.DataTree,
    variable_path: str,
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
    nc_xarray : xarray.DataTree
        xarray DataTree loaded from NetCDF file. This represents the whole
        file.
    variable_path: str
        Full of the variable within the file to convert.
    logger : logging.Logger
        Python Logger object for emitting log messages.

    Notes
    -----
    - Assumption that 0 is always on the prime meridian/equator.
    - The output name for converted GeoTIFFs is `<variable path>.tif`, with any
      slashes replaced with underscores.
    """
    # Filter a warning that comes when opening the src_dataset with rasterio in r+ mode,
    # "Source dataset should be opened in read-only mode. Use of datasets opened in modes
    # other than 'r' will be disallowed in a future version."
    # r+ mode is required to mutate the crs of the src_dataset for cog_translate
    warnings.filterwarnings(
        'ignore',
        message='Source dataset should be*',
        category=rasterio.RasterioDeprecationWarning
    )

    logger.debug('NetCDF Var: %s', variable_path)

    if variable_path in EXCLUDE_VARS:
        logger.debug(f'Variable {variable_path} is excluded. Will not produce COG')
        return None

    output_basename = f'{variable_path}.tif'.lstrip('/').replace('/', '_')
    output_file_name = path_join(output_directory, output_basename)

    with TemporaryDirectory() as tempdir:
        temp_file_name = path_join(tempdir, output_basename)

        try:
            if not is_valid_spatial_dimensions(
                nc_xarray[variable_path],
                variable_path,
                logger
            ):
                # The variable being processed does not have spatial dimensions:
                raise Net2CogError(
                    variable_path,
                    f'{variable_path} does not have spatial dimensions such as '
                    'lat/lon, x/y, latitude/longitude, x-dim/y-dim, or XDim/YDim',
                )
            nc_xarray[variable_path].rio.to_raster(temp_file_name, BIGTIFF='IF_SAFER')
        except KeyError:
            # Occurs when trying to locate a variable that is not in the DataTree
            logger.warning(
                f'Variable {variable_path} cannot be converted to tiff:'
                f" No variable named '{variable_path}'."
            )
            return None
        except (LookupError, TypeError) as err:
            logger.info('Variable %s cannot be converted to tif: %s',
                        variable_path, err)
            raise Net2CogError(variable_path, str(err)) from err
        except ValueError as error:
            process_value_error_exception(nc_xarray,
                                          variable_path,
                                          str(error),
                                          logger,
                                          temp_file_name)
        except InvalidDimensionOrder as dmerr:
            logger.info('%s: reorder dimensions...', dmerr)
            process_invalid_dimension_order_exception(nc_xarray,
                                                      variable_path,
                                                      logger,
                                                      temp_file_name)
        except MissingSpatialDimensionError as dmerr:
            logger.info('%s: No x or y xarray dimensions, adding them...', dmerr)
            process_missing_spatial_dimension_error_exception(nc_xarray,
                                                              variable_path,
                                                              logger,
                                                              temp_file_name)
        except DimensionError as dmerr:
            logger.info('%s: No x or y xarray dimensions, adding them...', dmerr)
            process_dimension_error_exception(nc_xarray,
                                              variable_path,
                                              logger,
                                              temp_file_name)

        logger.info('Starting conversion... %s', output_file_name)

        with rasterio.open(temp_file_name, mode='r+') as src_dataset:
            src_dataset.crs = get_crs_from_grid_mapping(
                nc_xarray, variable_path, logger
            )
            dst_profile = cog_profiles.get('deflate')
            dst_profile.update({'BIGTIFF': 'IF_SAFER'})
            cog_translate(
                src_dataset,
                output_file_name,
                dst_profile,
                use_cog_driver=True,
                progress_out=io.StringIO(),
            )

    logger.info('Finished conversion, writing variable: %s', output_file_name)
    logger.info('NetCDF conversion complete. Returning COG generated.')
    return output_file_name


def get_all_data_variables(
    root_datatree: xr.DataTree,
    logger: Logger,
) -> list[str]:
    """
    Traverse tree and retrieve all data variables in all groups.

    Parameters
    ----------
    root_datatree : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.

    Returns
    -------
    list[str]
        A list of paths to all variables in the `data_vars` property of any
        node in the DataTree. These variables are filtered to remove any
        variables that are 1-D, attribute-only (e.g., CRS definitions),
        dtype = string(S1/S2), or variable without dimensions.

    """
    data_variables = []
    # issue/8: use subtree iterator instead of to_dict() to conserve memory
    for node in root_datatree.subtree:
        if not (node.has_data and node.data_vars):
            continue

        for var_name in node.data_vars:
            var_name_str = str(var_name)
            var_path = construct_variable_path(node.path, var_name_str)

            # Filter variables based on shape, dtype, and spatial dimensions
            if (
                is_valid_shape(node[var_name_str], var_path, logger) and
                is_valid_dtype(node[var_name_str], var_path, logger) and
                is_valid_spatial_dimensions(node[var_name_str], var_path, logger)
            ):
                data_variables.append(var_path)

    return data_variables


def get_crs_from_grid_mapping(
    nc_xarray: xr.DataTree,
    variable_path: str,
    logger: Logger,
) -> CRS:
    """
    Check the metadata attributes for the variable to find the associated
    grid mapping variable.  If the grid mapping variable, as referred to in the
    grid_mapping CF-Convention metadata attribute, does not exist then
    default to "+proj=latlong".

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        xarray DataTree loaded from NetCDF file. This represents the whole
        file.
    variable_path: str
        Full of the variable within the file to convert.
    logger : logging.Logger
        Python Logger object for emitting log messages.

    Returns
    -------
    csr
        Returns a `CRS` object corresponding to a grid mapping variable.

    """
    # Default CRS EPSG:4326
    crs = CRS.from_epsg(4326)

    grid_mapping_attribute = nc_xarray[variable_path].attrs.get('grid_mapping')

    if grid_mapping_attribute is not None:
        cf_reference_attribute = resolve_relative_path(
            nc_xarray, variable_path, grid_mapping_attribute
        )

        try:
            if cf_reference_attribute is not None:
                cf_parameters = nc_xarray[cf_reference_attribute].attrs
                crs = pyCRS.from_cf(cf_parameters)
                logger.info('CRS: %s', crs)
        except CRSError as error:
            raise Net2CogError(
                variable_path, f"An unsupported target CRS. Use default CRS '{crs}'."
            ) from error

    return crs


def process_value_error_exception(
    nc_xarray: xr.DataTree,
    variable_path: str,
    error_message: str,
    logger: Logger,
    temp_file_name: str,
):
    """
    This function uses the error message to identify a suitable handler
    function that can transform the input DataTree to resolve the issue.
    It then retries the raster conversion using the corrected data.
    If the error persists or another exception occurs, it logs the
    failure and raises a Net2CogError.

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.
    variable_path: str
        Variable path is present in DataTree
    error_message: str
        The ValueError exception message
    logger : logging.Logger
        Python Logger object for emitting log messages.
    temp_file_name: str
        rio.to_raster outputs the processed .tif file to temp location

    """
    try:
        value_error_handler = get_value_error_handler(
            nc_xarray,
            variable_path,
            str(error_message)
        )
        logger.info('Calling %s() method...', value_error_handler)
        # net2cog issue #8: since we work with DataArray instead of DataTree
        # the error handler has been updated accordingly
        variable_data = value_error_handler(nc_xarray, variable_path)
        variable_data.rio.to_raster(temp_file_name, BIGTIFF='IF_SAFER')
    except ValueError as valerr:
        raise ValueError(valerr) from valerr
    except Exception as err:    # pylint: disable=broad-except
        logger.info('Variable %s cannot be converted to tif: %s',
                    variable_path, err)
        raise Net2CogError(variable_path, str(err)) from err


def process_invalid_dimension_order_exception(
    nc_xarray: xr.DataTree,
    variable_path: str,
    logger: Logger,
    temp_file_name: str,
):
    """
    This function uses the error message to identify a suitable handler
    function that can transform the input DataTree to resolve the issue.
    It then retries the raster conversion using the corrected data.
    If the error persists or another exception occurs, it logs the
    failure and raises a Net2CogError.

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.
    variable_path: str
        Variable path is present in DataTree
    logger : logging.Logger
        Python Logger object for emitting log messages.
    temp_file_name: str
        rio.to_raster outputs the processed .tif file to temp location

    """
    try:
        # reorder_dimensions now returns DataArray directly
        variable_data = reorder_dimensions(nc_xarray, variable_path)
        variable_data.rio.to_raster(temp_file_name, BIGTIFF='IF_SAFER')
    except Exception as err:    # pylint: disable=broad-except
        logger.info('Variable %s cannot be converted to tif: %s',
                    variable_path, err)
        raise Net2CogError(variable_path, str(err)) from err


def process_dimension_error_exception(
    nc_xarray: xr.DataTree,
    variable_path: str,
    logger: Logger,
    temp_file_name: str,
):
    """
    Handles an InvalidDimensionOrder exception by attempting
    to swap the dimensions of a NetCDF variable to match the expected
    spatial layout for raster conversion.

    This function applies a dimension swap strategy using
    `swap_dims` to correct issues where the variable's dimensions
    are not in a valid order for rasterization
    (e.g., time-first or non-spatial-first layouts). It then retries
    writing the variable to a temporary GeoTIFF file. If the conversion
    fails again, it logs the error and raises a `Net2CogError`.

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.
    variable_path: str
        Variable path is present in DataTree
    logger : logging.Logger
        Python Logger object for emitting log messages.
    temp_file_name: str
        rio.to_raster outputs the processed .tif file to temp location

    """
    try:
        nc_xarray_tmp = _rioxr_swapdims(nc_xarray)
        nc_xarray_tmp[variable_path].rio.to_raster(temp_file_name, BIGTIFF='IF_SAFER')
    except Exception as err:    # pylint: disable=broad-except
        logger.info('Variable %s cannot be converted to tif: %s',
                    variable_path, err)
        raise Net2CogError(variable_path, str(err)) from err


def process_missing_spatial_dimension_error_exception(
    nc_xarray: xr.DataTree,
    variable_path: str,
    logger: Logger,
    temp_file_name: str,
):
    """
    Handles an MissingSpatialDimensionError exception by attempting
    to reorder then rename coordinates to standard 'x' and 'y' required
    by rasterio

    This function uses a dimension renaming strategy with `.rename`
    to fix cases where the variable’s y/x dimensions are not found.
    By rename coordinates to standard 'x' and 'y' required by rasterio,
    the issue can be resolved. It then retries writing the variable to
    a temporary GeoTIFF file. If the conversion fails again, it logs
    the error and raises a `Net2CogError`.

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.
    variable_path: str
        Variable path is present in DataTree
    logger : logging.Logger
        Python Logger object for emitting log messages.
    temp_file_name: str
        rio.to_raster outputs the processed .tif file to temp location

    """
    try:
        # Both functions now return DataArray directly
        variable_data = reorder_dimensions(nc_xarray, variable_path)
        variable_data = rename_dimensions(variable_data)
        variable_data.rio.to_raster(temp_file_name, BIGTIFF='IF_SAFER')
    except Exception as err:    # pylint: disable=broad-except
        logger.info('Variable %s cannot be converted to tif: %s',
                    variable_path, err)
        raise Net2CogError(variable_path, str(err)) from err


def netcdf_converter(
    input_nc_file: pathlib.Path,
    output_directory: pathlib.Path,
    var_list: list[str],
    logger: Logger,
) -> list[str]:
    """
    Primary function for beginning NetCDF conversion using rasterio,
    rioxarray and xarray

    Parameters
    ----------
    input_nc_file : pathlib.Path
        Path to  NetCDF file to process
    output_directory : pathlib.Path
        Path to temporary directory into which results will be placed before
        staging in S3.
    var_list : list[str]
        List of variable names to be converted to various single band cogs,
        ex: ['gland', 'fland', 'sss_smap']. For hierarchical granules, these
        names will be full paths to the variable location in the file, omitting
        the leading slash, e.g.: 'Grid/precipitationCal'. If this list is
        empty, it is assumed that all data variables have been requested.
    logger : logging.Logger
        Python Logger object for emitting log messages.

    Notes
    -----
    Currently uses local file paths, no s3 paths
    """
    # Filter a warning about HDF-5 dimension access, not relevant to net2cog use case
    # "The 'phony_dims' kwarg now defaults to 'access'. Previously 'phony_dims=None'
    # would raise an error. For full netcdf equivalence please use phony_dims='sort'."
    warnings.filterwarnings(
        'ignore',
        message="The 'phony_dims'*",
        category=UserWarning
    )
    logger.info('Input file name: %s', input_nc_file)

    netcdf_file = os.path.abspath(input_nc_file)
    logger.debug('NetCDF Path: %s', netcdf_file)

    # recognized files will have engine == 'h5netcdf' or 'netcdf4'
    nc_engine = identify_file(netcdf_file)
    if nc_engine is None:
        raise Net2CogError(
            str(var_list),
            f'Not a NetCDF/HDF-5 file; Skipped file: {netcdf_file}'
        )

    logger.info('Reading %s', basename(netcdf_file))
    # Some granules have variables that can't be chunked
    use_chunks = not has_object_dtype_variables(netcdf_file)

    input_datatree = xr.open_datatree(
        netcdf_file,
        chunks='auto' if use_chunks else None,
        engine=nc_engine,
        decode_coords=False,
        decode_times=xr.coders.CFDatetimeCoder(use_cftime=False),
        decode_timedelta=False,
        concat_characters=True,
    )

    if not var_list:
        # Empty list means "all" variables, so get all variables in
        # the `xarray.DataTree`.
        var_list = get_all_data_variables(input_datatree, logger)

    raw_output_files = [
        _write_cogtiff(str(output_directory), input_datatree, variable_name, logger)
        for variable_name in var_list
    ]
    # Remove None returns, e.g., for excluded or non-existent variables
    output_files = [
        output_file
        for output_file in raw_output_files
        if output_file is not None
    ]

    # If all variables are invalid
    if output_files == []:
        raise Net2CogError(
            str(var_list),
            f'No output files generated for {netcdf_file}'
        )

    return output_files
