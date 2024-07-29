# pylint: disable=unused-import
"""
=========
netcdf-convert.py
=========

Functions related to converting a NetCDF file to other formats.
"""

import os
import pathlib
from os.path import join as pjoin, basename, dirname, exists, splitext
import subprocess
from subprocess import check_call

import logging
import tempfile
from typing import List

import xarray as xr
import rasterio
from rasterio import CRS

from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles

import rioxarray  # noqa
from rioxarray.exceptions import DimensionError

LOGGER = logging.getLogger(__name__)
EXCLUDE_VARS = ['lon', 'lat', 'longitude', 'latitude', 'time']


def run_command(command, work_dir):
    """
    A simple utility to execute a subprocess command.
    """
    try:
        out_call = check_call(command, stderr=subprocess.STDOUT, cwd=work_dir)
        return out_call
    except subprocess.CalledProcessError as err:
        LOGGER.error("command '%s' return with error (code %s): %s",
                     err.cmd, err.returncode, err.output)
        raise


def check_dir(fname):
    """
    To return filename and path without file extension
    """
    file_name = fname.split('/')
    rel_path = pjoin(*file_name[-2:])
    file_wo_extension, _ = splitext(rel_path)
    return file_wo_extension


def get_gtiff_name(output_file):
    """
    To create tmp filename to convert to COG and create a filename
    just as source but without '.TIF' extension
    """
    outf = os.path.basename(output_file)
    dir_path = dirname(output_file)
    rel_path = check_dir(outf)
    out_fname = pjoin(dir_path, rel_path)
    if not exists(out_fname):
        os.makedirs(out_fname)
    return pjoin(out_fname, rel_path)


def _write_cogtiff(out_f_name, nc_xarray):
    """
    This function converts each variable inside a NetCDF file into a
    cloud optimized geotiff.

    Parameters
    ----------
    out_f_name : string
        Path to temp gtiff filename excluding file extension
        example :/home/dockeruser/converter/podaac/netcdf_converter/temp/
            netcdf_converter/
            RSS_smap_SSS_L3_8day_running_2020_037_FNL_v04.0_test
    nc_xarray : xarray dataset
        xarray dataset loaded from NetCDF file

    Notes
    -----
    Assumption that 0 is always on the prime meridian/equator.
    """

    cogs_generated = []
    with tempfile.TemporaryDirectory() as tempdir:

        # variables in netcdf
        for var in nc_xarray.variables:
            if var in EXCLUDE_VARS:
                continue
            LOGGER.debug("NetCDF Var: %s", var)

            def rioxr_swapdims(netcdf_xarray):
                netcdf_xarray.coords['y'] = ('lat', netcdf_xarray.lat)
                netcdf_xarray.coords['x'] = ('lon', netcdf_xarray.lon)

                return netcdf_xarray.swap_dims({'lat': 'y', 'lon': 'x'})

            # copy to a tempfolder
            out_fname = out_f_name + '_' + var + '.tif'
            temp_fname = pjoin(tempdir, basename(out_fname))

            try:
                nc_xarray[var].rio.to_raster(temp_fname)
            except LookupError as err:
                LOGGER.info("Variable %s cannot be converted to tif: %s", var, err)
                continue
            except DimensionError as dmerr:
                try:
                    LOGGER.info("%s: No x or y xarray dimensions, adding them...", dmerr)
                    nc_xarray_tmp = rioxr_swapdims(nc_xarray)
                    nc_xarray_tmp[var].rio.to_raster(temp_fname)
                except RuntimeError as runerr:
                    LOGGER.info("Variable %s cannot be converted to tif: %s", var, runerr)
                    continue
                except Exception as aerr:  # pylint: disable=broad-except
                    LOGGER.info("Variable %s cannot be converted to tif: %s", var, aerr)
                    continue

            # Option to add additional GDAL config settings
            # config = dict(GDAL_NUM_THREADS="ALL_CPUS", GDAL_TIFF_OVR_BLOCKSIZE="128")
            # with rasterio.Env(**config):

            LOGGER.info("Starting conversion... %s", out_fname)

            # default CRS setting
            # crs = rasterio.crs.CRS({"init": "epsg:3857"})

            with rasterio.open(temp_fname, mode='r+') as src_dataset:
                # if src_dst.crs is None:
                #     src_dst.crs = crs
                src_dataset.crs = CRS.from_proj4(proj="+proj=latlong")
                dst_profile = cog_profiles.get("deflate")
                cog_translate(src_dataset, out_fname, dst_profile, use_cog_driver=True)

            cogs_generated.append(out_fname)
            LOGGER.info("Finished conversion, writing variable: %s", out_fname)
    LOGGER.info("NetCDF conversion complete. Returning COGs generated.")
    return cogs_generated


def netcdf_converter(input_nc_file: pathlib.Path, output_cog_pathname: pathlib.Path, var_list: list = ()) -> List[str]:
    """
    Primary function for beginning NetCDF conversion using rasterio,
    rioxarray and xarray

    Parameters
    ----------
    input_nc_file : pathlib.Path
        Path to  NetCDF file to process
    output_cog_pathname : pathlib.Path
        COG Output path and NetCDF filename, filename converted to cog variable
        filename (.tif)
            ex: tests/data/tmpygj2vgxf/
            RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc
    var_list : list
        List of variable names to be converted to various single band cogs,
        ex: ['gland', 'fland', 'sss_smap']

    Notes
    -----
    Currently uses local file paths, no s3 paths
    """

    netcdf_file = os.path.abspath(input_nc_file)
    LOGGER.debug('NetCDF Path: %s', netcdf_file)

    gtiff_fname = get_gtiff_name(output_cog_pathname)

    if netcdf_file.endswith('.nc'):
        LOGGER.info("Reading %s", basename(netcdf_file))
        LOGGER.info('Tmp GTiff filename: %s', gtiff_fname)

        xds = xr.open_dataset(netcdf_file)

        # NetCDF must have spatial dimensions
        if (({"lon", "lat"}.issubset(set(xds.dims)))
                or ({"longitude", "latitude"}.issubset(set(xds.dims)))
                or ({"x", "y"}.issubset(set(xds.dims)))):
            # used to invert y axis
            # xds_reversed = xds.reindex(lat=xds.lat[::-1])
            LOGGER.info("Writing COG to %s", basename(gtiff_fname))
            if var_list:
                xds = xds[var_list]
            return _write_cogtiff(gtiff_fname, xds)
        LOGGER.error("%s: NetCDF file does not contain spatial dimensions such as lat / lon "
                     "or x / y", netcdf_file)
        return []
    LOGGER.info("Not a NetCDF file; Skipped file: %s", netcdf_file)
    return []
