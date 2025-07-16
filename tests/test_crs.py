"""
==============
test_crs.py
==============

Test the net2cog utilites functionality.
"""

import pathlib
import os

import pytest
import xarray as xr
from rasterio.crs import CRS

from net2cog.netcdf_convert import (
    Net2CogError,
    get_crs_from_grid_mapping,
)


def test_crs_nested_path_same_group(temp_dir, logger, spl2smp_nested_file):
    """Test CRS variable with nested path same group"""

    test_crs = CRS.from_epsg(6933)
    test_file = pathlib.Path(temp_dir, spl2smp_nested_file)
    netcdf_file = os.path.abspath(test_file)
    input_datatree = xr.open_datatree(netcdf_file)

    # Process test file:
    output_crs = get_crs_from_grid_mapping(
        input_datatree, "Soil_Moisture_Retrieval_Data/vegetation_water_content", logger
    )

    assert output_crs.to_epsg() == test_crs.to_epsg()
    assert output_crs.is_projected


def test_crs_nested_path_root_group(temp_dir, logger, nested_file):
    """Test CRS variable with nested path at root group"""

    test_crs = CRS.from_epsg(6933)
    test_file = pathlib.Path(temp_dir, nested_file)
    netcdf_file = os.path.abspath(test_file)
    input_datatree = xr.open_datatree(netcdf_file)

    # Process test file:
    output_crs = get_crs_from_grid_mapping(input_datatree, "NEE/nee_mean", logger)

    assert output_crs.to_epsg() == test_crs
    assert output_crs.is_projected


def test_crs_multiple_variable_selection_no_grid_mapping(temp_dir, smap_file, logger):
    """Test the default EPSG:4326 CRS variable's handling of the absence of grid
    mapping attributes.

    """

    test_file = pathlib.Path(temp_dir, smap_file)

    netcdf_file = os.path.abspath(test_file)
    input_datatree = xr.open_datatree(netcdf_file)

    # Process test file:
    output_crs = get_crs_from_grid_mapping(input_datatree, "sss_smap", logger)

    result_crs = output_crs.to_epsg()

    assert result_crs == 4326
    assert output_crs.is_geographic


def test_pyCRS_from_cf_handle_exception(logger, input_datatree):
    """Ensure that pyCRS.from_cf() catch CRSError exception and rethrows
    Net2CogError if error processings a grid-mapping.

    The following test will raise an exception because
    group_five/variable_one grid_mapping attribute points to science_one,
    references a dataset that lacks the required cf_parameters

    Tree structure in input_datatree:

    |- science_one(lat, lon)
    |- lat(lat)
    |- lon(lon)
    |- group_one
       |- science_two(lat, lon)
       |- science_three(lat, lon)
       |- group_two
          | science_four(lat, lon)
    |- group_five
       |- variable_one(attr: grid_mapping: science_one)

    """

    with pytest.raises(Net2CogError):
        get_crs_from_grid_mapping(input_datatree, "group_five/variable_one", logger)
