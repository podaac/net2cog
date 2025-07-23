"""
==============
test_utilities.py
==============

Test the net2cog utilites functionality.
"""

import pytest
import numpy as np
import xarray as xr
from net2cog.netcdf_convert import Net2CogError
from net2cog.utilities import (
    resolve_relative_path,
    is_variable_in_datatree,
    reorder_dimensions,
    is_valid_spatial_dimensions,
)


def test_resolve_relative_path(input_datatree):
    """Ensure a relative path can be qualified to a full path using the
    location of the dataset making the reference.

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
       |- variable_one(attr: grid_mapping)

    """

    test_args = [
        [
            "Single variable not absolute",
            "science_one",
            "science_one",
            "/science_one",
        ],
        [
            "Single variable absolute",
            "science_one",
            "/science_one",
            "/science_one",
        ],
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
            "Nested relative path ../",
            "group_one/science_two",
            "../science_one",
            "science_one",
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
        [
            "Reference is in the same group as this variable ./",
            "group_one/science_two",
            "./science_three",
            "group_one/science_three",
        ],
    ]

    for description, variable_path, reference_path, expected_path in test_args:
        print(description)
        resolved_path = resolve_relative_path(
            input_datatree, variable_path, reference_path
        )

        assert resolved_path == expected_path


def test_resolve_relative_path_handle_exception(input_datatree):
    """Ensure that unresolved paths result in a None return

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
       |- variable_one(attr: grid_mapping)

    """

    # Negative test
    test_args = [
        [
            "Test resolve_relative_path() handle excpetion for relative path incorrect nesting",
            "group_one/science_two",
            "group_one/science_four",
        ],
        [
            "Test resolve_relative_path() handle excpetion for variable reference not in Datatree",
            "group_one/science_three",
            "science_three_half",
        ],
        [
            "Test resolve_relative_path() handle excpetion for double nested cross group not in Datatree",
            "group_one/science_two",
            "group_one/group_two/science_two",
        ],
    ]

    for description, variable_path, reference_path in test_args:
        print(description)
        with pytest.raises(Net2CogError):
            resolve_relative_path(input_datatree, variable_path, reference_path)


def test_is_variable_in_datatree(input_datatree):
    """Ensure the absolute reference path is present in DataTree.

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
       |- variable_one(attr: grid_mapping)

    """

    test_args = [
        [
            "Test is_variable_in_datatree() single absolute reference path",
            "/science_one",
        ],
        [
            "Test is_variable_in_datatree() nested relative reference path",
            "/group_one/science_three",
        ],
        [
            "Test is_variable_in_datatree() double nested cross group relative path",
            "/group_one/group_two/science_four",
        ],
        [
            "Test is_variable_in_datatree() reference is in the same group as this variable ./",
            "/group_one/science_three",
        ],
    ]

    for description, reference_path in test_args:
        print(description)
        resolved_path = is_variable_in_datatree(input_datatree, reference_path)

        assert resolved_path


def test_variable_not_in_datatree(input_datatree):
    """Ensure the absolute reference path is not present in DataTree.

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
       |- variable_one(attr: grid_mapping)

    """

    test_args = [
        [
            "Negative test is_variable_in_datatree() single absolute reference path",
            "/science_one_half",
        ],
        [
            "Negative test is_variable_in_datatree() nested relative reference path",
            "/group_one/science_three_half",
        ],
        [
            "Negative test is_variable_in_datatree() double nested cross group relative path",
            "/group_one/group_two/science_four_half",
        ],
        [
            "Negative test is_variable_in_datatree() reference is in the same group as this variable ./",
            "/group_one/science_three_half",
        ],
    ]

    for description, reference_path in test_args:
        print(description)
        resolved_path = is_variable_in_datatree(input_datatree, reference_path)

        assert resolved_path is False


def test_reorder_2d_lon_lat(input_datatree_reorder_2d_lon_lat):
    """Ensure that a 2-dimensional lon, lat array is reordered using
    DataTree.transpose() to create the correct dimension
    order in a new DataTree

    Tree structure in input_datatree:

    |- science_one(lon, lat)
    |- lat(lat)
    |- lon(lon)

    """

    description = "Test reordered (lon, lat) to (lat, lon)"
    variable_path = "science_one"
    expected_path = ("lat", "lon")

    print(description)
    nc_xarray_tmp = reorder_dimensions(input_datatree_reorder_2d_lon_lat, variable_path)

    assert nc_xarray_tmp[variable_path].dims == expected_path


def test_reorder_2d_longitude_latitude(input_datatree_reorder_2d_longitude_latitude):
    """Ensure that a 2-dimensional longitude, latitude) array is reordered using
    DataTree.transpose() to create the correct dimension
    order in a new DataTree

    Tree structure in input_datatree:

    |- science_two(longitude, latitude)
    |- latitude(lat)
    |- longitude(lon)

    """
    description = "Test reordered (longitude, latitude) to (latitude, longitude)"
    variable_path = "science_two"
    expected_path = ("latitude", "longitude")

    print(description)
    nc_xarray_tmp = reorder_dimensions(
        input_datatree_reorder_2d_longitude_latitude, variable_path
    )

    assert nc_xarray_tmp[variable_path].dims == expected_path


def test_reorder_2d_x_y(input_datatree_reorder_2d_x_y):
    """Ensure that a 2-dimensional x, y array is reordered using
    DataTree.transpose() to create the correct dimension
    order in a new DataTree

    Tree structure in input_datatree:

    |- science_three(x, y)
    |- x(x)
    |- y(y)

    """

    description = "Test reordered (x, y) to (y, x)"
    variable_path = "science_three"
    expected_path = ("y", "x")

    print(description)
    nc_xarray_tmp = reorder_dimensions(input_datatree_reorder_2d_x_y, variable_path)

    assert nc_xarray_tmp[variable_path].dims == expected_path


def test_reorder_2d_x_dim_y_dim(input_datatree_reorder_2d_x_dim_y_dim):
    """Ensure that a 2-dimensional x_dim y_dim array is reordered using
    DataTree.transpose() to create the correct dimension
    order in a new DataTree

    Tree structure in input_datatree:

    |- science_four(x-dim, y-dim)
    |- x-dim(x-dim)
    |- y-dim(y-dim)

    """

    description = "Test reordered (x-dim, y-dim) to (y-dim, x-dim)"
    variable_path = "science_four"
    expected_path = ("y-dim", "x-dim")

    print(description)
    nc_xarray_tmp = reorder_dimensions(
        input_datatree_reorder_2d_x_dim_y_dim, variable_path
    )

    assert nc_xarray_tmp[variable_path].dims == expected_path


def test_reorder_3d_dimensions(input_datatree_reorder_3d):
    """Ensure that a 3-dimensional array is reordered using
    DataTree.transpose() to create the correct dimension
    order in a new DataTree

    Tree structure in input_datatree:

    |- science_one(lat, lon, time)
    |- lat(lat)
    |- lon(lon)
    |- time(tim)
    |- group_one
       |- science_two(latitude, longitude, time)
    |- group_two
       |- science_three(x, y, z)
        |- group_four
          | science_four(x-dim, y-dim, z-dim)
    |- group_four
       |- science_five(abc, def, ghi)

    """

    test_args = [
        [
            "Test reordered (lat, lon, time) to (time, lat, lon)",
            "science_one",
            ("time", "lat", "lon"),
        ],
        [
            "Test reordered (latitude, longitude, time) to (time, latitude, longitude)",
            "group_one/science_two",
            ("time", "latitude", "longitude"),
        ],
        [
            "Test reordered (x, y, z) to (z, y, x)",
            "group_two/science_three",
            ("z", "y", "x"),
        ],
        [
            "Test reordered (x-dim, y-dim, z-dim) to (z-dim, y-dim, x-dim)",
            "group_two/group_three/science_four",
            ("z-dim", "y-dim", "x-dim"),
        ],
    ]

    for description, variable_path, expected_path in test_args:
        print(description)
        nc_xarray_tmp = reorder_dimensions(input_datatree_reorder_3d, variable_path)

        assert nc_xarray_tmp[variable_path].dims == expected_path


def test_reorder_3d_dimensions_exception(input_datatree_reorder_3d):
    """Ensure that the function handles exceptions when missing
    coordinates are not parsed correctly.

    Tree structure in input_datatree:

    |- science_one(lat, lon, time)
    |- lat(lat)
    |- lon(lon)
    |- time(tim)
    |- group_one
       |- science_two(latitude, longitude, time)
    |- group_two
       |- science_three(x, y, z)
        |- group_four
          | science_four(x-dim, y-dim, z-dim)
    |- group_four
       |- science_five(abc, def, ghi)
    |- group_five
       |- science_six(y, x, '')
    |- group_six
       |- science_six(y, x, z, w)

    """

    test_args = [
        [
            "Test Net2CogError (abc, def, ghi) x,y not exisit",
            "group_four/science_five",
            None,
        ],
        [
            "Test Net2CogError (y, x, '') z is empty string",
            "group_five/science_six",
            None,
        ],
        [
            "Test Net2CogError for 4 dimension (y, x, z, w)",
            "group_six/science_seven",
            None,
        ],
    ]

    for description, variable_path, expected_path in test_args:
        print(description)
        with pytest.raises(Net2CogError):
            reorder_dimensions(input_datatree_reorder_3d, variable_path)


@pytest.mark.parametrize(
    'dimensions',
    [['lat', 'lon'], ['latitude', 'longitude'], ['x', 'y'], ['x-dim', 'y-dim']],
)
def test_is_valid_spatial_dimensions_present(dimensions, logger):
    """Verify returns True for variable with spatial dimensions."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={'science': ([dimensions[0], dimensions[1]], np.ones((2, 4)))},
            coords={
                dimensions[0]: (dimensions[0], np.array([1, 2])),
                dimensions[1]: (dimensions[1], np.array([3, 4, 5, 6])),
            },
        ),
    )
    assert is_valid_spatial_dimensions(test_datatree['science'], 'science', logger)


@pytest.mark.parametrize(
    'dimensions',
    [['lat', 'lon'], ['latitude', 'longitude'], ['x', 'y'], ['x-dim', 'y-dim']],
)
def test_is_valid_spatial_dimensions_and_others_present(dimensions, logger):
    """Verify returns True, when spatial dimensions and others are present."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                'science': (['time', dimensions[0], dimensions[1]], np.ones((1, 2, 4)))
            },
            coords={
                'time': ('time', np.array([0])),
                dimensions[0]: (dimensions[0], np.array([1, 2])),
                dimensions[1]: (dimensions[1], np.array([3, 4, 5, 6])),
            },
        ),
    )
    assert is_valid_spatial_dimensions(test_datatree['science'], 'science', logger)


@pytest.mark.parametrize('dimension', ['lat', 'latitude', 'x', 'x-dim'])
def test_is_valid_spatial_dimensions_incomplete(dimension, logger):
    """Verify returns False when only one spatial dimension present."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={'science': ([dimension], np.ones((4)))},
            coords={
                dimension: (dimension, np.array([1, 2, 3, 4])),
            },
        ),
    )
    assert not is_valid_spatial_dimensions(test_datatree['science'], 'science', logger)


def test_is_valid_spatial_dimensions_absent(logger):
    """Verify returns False for variable without spatial dimensions."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={'science': (['time'], np.ones(4))},
            coords={
                'time': ('time', np.array([1, 2, 3, 4])),
            },
        ),
    )
    assert not is_valid_spatial_dimensions(test_datatree['science'], 'science', logger)
