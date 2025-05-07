"""
==============
test_crs.py
==============

Test the net2cog utilites functionality.
"""

import pathlib
import os
from textwrap import dedent

import numpy as np
import xarray as xr
import rasterio
from rasterio.crs import CRS

from net2cog.netcdf_convert import (
    get_crs_from_grid_mapping,
)
from net2cog.utilities import (
    resolve_relative_path
)

# Test constants
WKT_EPSG_6933 = dedent(
    """
    PROJCRS["WGS 84 / NSIDC EASE-Grid 2.0 Global",
    BASEGEOGCRS["WGS 84",
        ENSEMBLE["World Geodetic System 1984 ensemble",
            MEMBER["World Geodetic System 1984 (Transit)"],
            MEMBER["World Geodetic System 1984 (G730)"],
            MEMBER["World Geodetic System 1984 (G873)"],
            MEMBER["World Geodetic System 1984 (G1150)"],
            MEMBER["World Geodetic System 1984 (G1674)"],
            MEMBER["World Geodetic System 1984 (G1762)"],
            MEMBER["World Geodetic System 1984 (G2139)"],
            MEMBER["World Geodetic System 1984 (G2296)"],
            ELLIPSOID["WGS 84",6378137,298.257223563,
                LENGTHUNIT["metre",1]],
            ENSEMBLEACCURACY[2.0]],
        PRIMEM["Greenwich",0,
            ANGLEUNIT["degree",0.0174532925199433]],
        ID["EPSG",4326]],
    CONVERSION["US NSIDC EASE-Grid 2.0 Global",
        METHOD["Lambert Cylindrical Equal Area",
            ID["EPSG",9835]],
        PARAMETER["Latitude of 1st standard parallel",30,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8823]],
        PARAMETER["Longitude of natural origin",0,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8802]],
        PARAMETER["False easting",0,
            LENGTHUNIT["metre",1],
            ID["EPSG",8806]],
        PARAMETER["False northing",0,
            LENGTHUNIT["metre",1],
            ID["EPSG",8807]]],
    CS[Cartesian,2],
        AXIS["easting (X)",east,
            ORDER[1],
            LENGTHUNIT["metre",1]],
        AXIS["northing (Y)",north,
            ORDER[2],
            LENGTHUNIT["metre",1]],
    USAGE[
        SCOPE["Environmental science - used as basis for EASE grid."],
        AREA["World between 86°S and 86°N."],
        BBOX[-86,-180,86,180]],
    ID["EPSG",6933]]
    """
)

WKT_EPSG_9835 = dedent(
    """
PROJCRS["undefined",
    BASEGEOGCRS["undefined",
        ENSEMBLE["World Geodetic System 1984 ensemble",
            MEMBER["World Geodetic System 1984 (Transit)",
                ID["EPSG",1166]],
            MEMBER["World Geodetic System 1984 (G730)",
                ID["EPSG",1152]],
            MEMBER["World Geodetic System 1984 (G873)",
                ID["EPSG",1153]],
            MEMBER["World Geodetic System 1984 (G1150)",
                ID["EPSG",1154]],
            MEMBER["World Geodetic System 1984 (G1674)",
                ID["EPSG",1155]],
            MEMBER["World Geodetic System 1984 (G1762)",
                ID["EPSG",1156]],
            MEMBER["World Geodetic System 1984 (G2139)",
                ID["EPSG",1309]],
            MEMBER["World Geodetic System 1984 (G2296)",
                ID["EPSG",1383]],
            ELLIPSOID["WGS 84",6378137,298.257223563,
                LENGTHUNIT["metre",1],
                ID["EPSG",7030]],
            ENSEMBLEACCURACY[2.0],
            ID["EPSG",6326]],
        PRIMEM["Greenwich",0,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8901]]],
    CONVERSION["unknown",
        METHOD["Lambert Cylindrical Equal Area",
            ID["EPSG",9835]],
        PARAMETER["Latitude of 1st standard parallel",30,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8823]],
        PARAMETER["Longitude of natural origin",0,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8802]],
        PARAMETER["False easting",0,
            LENGTHUNIT["metre",1],
            ID["EPSG",8806]],
        PARAMETER["False northing",0,
            LENGTHUNIT["metre",1],
            ID["EPSG",8807]]],
    CS[Cartesian,2],
        AXIS["(E)",east,
            ORDER[1],
            LENGTHUNIT["metre",1,
                ID["EPSG",9001]]],
        AXIS["(N)",north,
            ORDER[2],
            LENGTHUNIT["metre",1,
                ID["EPSG",9001]]]]
    """
)


def test_crs_nested_path_same_group(temp_dir, logger, spl2smp_nested_file):
    """Test CRS variable with nested path same group"""

    test_crs = CRS.from_wkt(WKT_EPSG_6933)
    test_file = pathlib.Path(temp_dir, spl2smp_nested_file)
    netcdf_file = os.path.abspath(test_file)
    input_datatree = xr.open_datatree(netcdf_file)

    # Process test file:
    rasterio.crs = get_crs_from_grid_mapping(
        input_datatree, "Soil_Moisture_Retrieval_Data/vegetation_water_content", logger
    )

    result_crs = rasterio.crs.to_wkt(pretty=True)

    assert result_crs == test_crs
    assert rasterio.crs.is_projected


def test_crs_nested_path_root_group(temp_dir, logger, nested_file):
    """Test CRS variable with nested path at root group"""

    test_crs = CRS.from_wkt(WKT_EPSG_9835)
    test_file = pathlib.Path(temp_dir, nested_file)
    netcdf_file = os.path.abspath(test_file)
    input_datatree = xr.open_datatree(netcdf_file)

    # Process test file:
    rasterio.crs = get_crs_from_grid_mapping(input_datatree, "NEE/nee_mean", logger)

    result_crs = rasterio.crs.to_wkt(pretty=True)

    assert result_crs == test_crs
    assert rasterio.crs.is_projected


def test_crs_multiple_variable_selection_no_grid_mapping(temp_dir, smap_file, logger):
    """Test the default EPSG:4326 CRS variable's handling of the absence of grid
    mapping attributes.

    """

    test_file = pathlib.Path(temp_dir, smap_file)

    netcdf_file = os.path.abspath(test_file)
    input_datatree = xr.open_datatree(netcdf_file)

    # Process test file:
    rasterio.crs = get_crs_from_grid_mapping(input_datatree, "sss_smap", logger)

    result_crs = rasterio.crs.to_epsg()

    assert result_crs == 4326
    assert rasterio.crs.is_geographic


def test_resolve_relative_path(logger):
    """Ensure a relative path can be qualified to a full path using the
    location of the dataset making the reference.

    Tree structure in test:

    |- science_one(lat, lon)
    |- lat(lat)
    |- lon(lon)
    |- group_one
       |- science_two(lat, lon)
       |- science_three(lat, lon)
       |- group_two
          | science_four(lat, lon)

    """
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_one": (["lat", "lon"], np.ones((2, 3))),
            },
            coords={
                "lat": ("lat", np.array([1, 2])),
                "lon": ("lon", np.array([3, 4, 5])),
            },
        )
    )
    test_datatree["group_one"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_two": (["lat", "lon"], np.ones((2, 3))),
            },
        ),
    )
    test_datatree["group_one"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_three": (["lat", "lon"], np.ones((2, 3))),
            },
        ),
    )
    test_datatree["group_one/group_two"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_four": (["lat", "lon"], np.ones((2, 3))),
            },
        ),
    )

    test_args = [
        [
            "Nested absolute path",
            "group_one/science_two",
            "/science_one",
            "/science_one",
        ],
        [
            "Nested relative path",
            "group_one/science_two",
            "science_three",
            "group_one/science_three",
        ],
        [
            "Double nested relative path",
            "group_one/group_two/science_four",
            "science_one",
            "/science_one",
        ],
        [
            "Double nested cross group relative path",
            "group_one/science_two",
            "group_one/group_two/science_four",
            "/group_one/group_two/science_four",
        ],
    ]

    for description, variable_path, reference_path, expected_path in test_args:
        print(description)
        resolved_path = resolve_relative_path(
            test_datatree, variable_path, reference_path, logger
        )

        assert resolved_path == expected_path

    # Negative test
    test_args = [
        [
            "Relative path has incorrect nesting",
            "group_one/science_two",
            "group_one/science_four",
            None,
        ],
        [
            "Variable reference not in Datatree",
            "group_one/science_three",
            "science_three_half",
            None,
        ],
        [
            "Double nested cross group not in Datatree",
            "group_one/science_two",
            "group_one/group_two/science_two",
            None,
        ],
    ]

    for description, variable_path, reference_path, expected_path in test_args:
        print(description)
        resolved_path = resolve_relative_path(
            test_datatree, variable_path, reference_path, logger
        )

        assert resolved_path == expected_path
