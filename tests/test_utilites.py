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
    get_dim_names_from_cf_standard_name_units,
    get_value_error_handler,
    apply_fillvalue_to_missing_value,
    get_fillvalue_and_missing_value,
    rename_dimensions,
    apply_datetime_conversion,
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
    variable_data = reorder_dimensions(input_datatree_reorder_2d_lon_lat, variable_path)

    assert variable_data.dims == expected_path


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
    variable_data = reorder_dimensions(
        input_datatree_reorder_2d_longitude_latitude, variable_path
    )

    assert variable_data.dims == expected_path


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
    variable_data = reorder_dimensions(input_datatree_reorder_2d_x_y, variable_path)

    assert variable_data.dims == expected_path


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
    variable_data = reorder_dimensions(
        input_datatree_reorder_2d_x_dim_y_dim, variable_path
    )

    assert variable_data.dims == expected_path


def test_reorder_2d_XDim_YDim(input_datatree_2d_XDim_YDim):
    """Ensure that a 2-dimensional XDim YDim array is reordered using
    DataTree.transpose() to create the correct dimension
    order in a new DataTree

    Tree structure in input_datatree:

    |- science_five(XDim, YDim)
    |- XDim
    |- YDim

    """

    description = "Test reordered (XDim, YDim) to (YDim, XDim)"
    variable_path = "science_one"
    expected_path = ("YDim", "XDim")

    print(description)
    variable_data = reorder_dimensions(
        input_datatree_2d_XDim_YDim, variable_path
    )

    assert variable_data.dims == expected_path


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
    |- group_seven
       |- science_eight(XDim, YDim, ZDim)

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
        [
            "Test reordered (XDim, YDim, ZDim) to (ZDim, YDim, XDim)",
            "group_four/science_five",
            ("ZDim", "YDim", "XDim"),
        ],
    ]

    for description, variable_path, expected_path in test_args:
        print(description)
        variable_data = reorder_dimensions(input_datatree_reorder_3d, variable_path)

        assert variable_data.dims == expected_path


def test_reorder_3d_dimensions_exception(input_datatree_bad_3d_variables):
    """Ensure that the function handles exceptions when missing
    coordinates are not parsed correctly.

    """

    test_args = [
        [
            "Test Net2CogError (abc, def, ghi) x,y not exisit",
            "group_one/science_one",
            None,
        ],
        [
            "Test Net2CogError (y, x, '') z is empty string",
            "group_two/science_two",
            None,
        ],
        [
            "Test Net2CogError for 4 dimension (y, x, z, w)",
            "group_three/science_three",
            None,
        ],
    ]

    for description, variable_path, expected_path in test_args:
        print(description)
        with pytest.raises(Net2CogError):
            reorder_dimensions(input_datatree_bad_3d_variables, variable_path)


@pytest.mark.parametrize(
    'dimensions',
    [['lat', 'lon'], ['latitude', 'longitude'], ['x', 'y'], ['x-dim', 'y-dim'],
     ['XDim', 'YDim']],
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
    [['lat', 'lon'], ['latitude', 'longitude'], ['x', 'y'], ['x-dim', 'y-dim'],
     ['XDim', 'YDim']],
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
    print('Test variable.dim returns False when only one spatial dimension present')
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
    print('For variables (time) that do not have spatial dimensions, test returns False')
    assert not is_valid_spatial_dimensions(test_datatree['science'], 'science', logger)


def test_is_valid_spatial_dimensions_XDim_YDim(input_datatree_2d_XDim_YDim, logger):
    """Verify returns True, when spatial dimensions and others are present.
    
        |- science_one(XDim, YDim)
        |- XDim
        |- YDim
        |- group_one
            |- science_two(xDim, yDim)
        |- group_two
            |- science_three(Xdim, Ydim)
        |- group_three
            |- science_four(XDIM, YDIM)
        |- group_four
            |- science_five(xdim, ydim)

    """
    test_args = [
        [
            "Test XDim/YDim is valid spatial dimensions",
            "science_one",
            ("XDim", "YDim"),
        ],
        [
            "Test xDim/yDim is valid spatial dimensions",
            "group_one/science_two",
            ("xDim", "yDim"),
        ],
        [
            "Test xDim/yDim is valid spatial dimensions",
            "group_two/science_three",
            ("Xdim", "Ydim"),
        ],
        [
            "Test XDIM/YDIM is valid spatial dimensions",
            "group_three/science_four",
            ("XDIM", "YDIM"),
        ],
        [
            "Test xdim/ydim is valid spatial dimensions",
            "group_four/science_five",
            ("xdim", "ydim"),
        ],
    ]

    for description, variable_path, expected_path in test_args:
        print(description)
        assert is_valid_spatial_dimensions(input_datatree_2d_XDim_YDim, variable_path, logger)


@pytest.mark.parametrize('dimension', ['XDim', 'y-dim'])
def test_is_valid_spatial_dimensions_XDim_y_dim_incomplete(dimension, logger):
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


def test_is_valid_spatial_dimensions_with_invalid_dim_names_with_valid_standard_name_units_success(logger):
    """Verify returns True, when spatial dimensions has invalid dim name 'latlat' and 'lonlong
    with correct standard_name and units."""
    coords = {
        "latlat": xr.DataArray([0], attrs={"standard_name": "latitude", "units": "degrees_north"}),
        "lonlon": xr.DataArray([0], attrs={"standard_name": "longitude", "units": "degrees_east"})
    }
    variable = xr.DataArray([1], coords=coords)
    assert is_valid_spatial_dimensions(variable, "science", logger)


def test_get_dim_names_from_cf_standard_name_units_success_lat_lon():
    """Verify returns dimension name "lat" and "lon" when spatial
    dimensions has correct standard_name and units.
    
    """
    coords = {
        "lat": xr.DataArray([0], attrs={"standard_name": "latitude", "units": "degrees_north"}),
        "lon": xr.DataArray([0], attrs={"standard_name": "longitude", "units": "degrees_east"})
    }
    variable = xr.DataArray([1], coords=coords)
    x_dim, y_dim = get_dim_names_from_cf_standard_name_units(variable)
    assert x_dim ==  "lon" and y_dim ==  "lat"


def test_get_dim_names_from_cf_standard_name_units_success_xdim_ydim():
    """Verify returns dimension name "XDim" and "YDim" when spatial
    dimensions has correct standard_name and units.
    
    """
    coords = {
        "XDim": xr.DataArray([0], attrs={"standard_name": "projection_x_coordinate", "units": "m"}),
        "YDim": xr.DataArray([0], attrs={"standard_name": "projection_y_coordinate", "units": "m"})
    }
    variable = xr.DataArray([1], coords=coords)
    x_dim, y_dim = get_dim_names_from_cf_standard_name_units(variable)
    assert x_dim ==  "XDim" and y_dim ==  "YDim"


def test_uppercase_dimensions_name_with_standard_name_units():
    """Verify returns dimension name "Latitude" and "Longitude" when spatial
    dimensions also has standard_name 'time' and units ' since '.
    
    """
    coords = {
        "Latitude": xr.DataArray([0], attrs={"standard_name": "latitude", "units": "degrees_north"}),
        "Longitude": xr.DataArray([0], attrs={"standard_name": "longitude", "units": "degrees_east"}),
        "time": xr.DataArray([0], attrs={"standard_name": "time", "units": "hours since 2001-01-01 00:00:00.0"})
    }
    variable = xr.DataArray([1], coords=coords)
    x_dim, y_dim = get_dim_names_from_cf_standard_name_units(variable)
    assert x_dim ==  "Longitude" and y_dim ==  "Latitude"


def test_missing_standard_name():
    """Verify returns dimension name "abc" and "def" when spatial
    dimensions does not have standard_name and valid units.
    
    """
    coords = {
        "abc": xr.DataArray([0], attrs={"units": "degrees_north"}),
        "def": xr.DataArray([0], attrs={"standard_name": "longitude", "units": "degrees_east"})
    }
    variable = xr.DataArray([1], coords=coords)
    x_dim, y_dim = get_dim_names_from_cf_standard_name_units(variable)
    assert x_dim ==  "def" and y_dim ==  "abc"


def test_missing_units():
    """Verify returns dimension name uppercase and cat "Lat" and "Lon"
    when spatial dimensions does not have units."""
    coords = {
        "Lat": xr.DataArray([0], attrs={"standard_name": "latitude", "units": "degrees_north"}),
        "Lon": xr.DataArray([0], attrs={"standard_name": "longitude"})
    }
    variable = xr.DataArray([1], coords=coords)
    x_dim, y_dim = get_dim_names_from_cf_standard_name_units(variable)
    assert x_dim ==  "Lon" and y_dim ==  "Lat"

def test_invalid_standard_name_and_units(logger):
    """Verify returns False, when spatial dimensions have invalid units."""
    coords = {
        "lat": xr.DataArray([0], attrs={"standard_name": "lat", "units": "degrees_nor"}),
        "lon": xr.DataArray([0], attrs={"standard_name": "lon", "units": "degrees_ea"})
    }
    variable = xr.DataArray([1], coords=coords)
    assert get_dim_names_from_cf_standard_name_units(variable) == (None, None)

def test_empty_coords(logger):
    """Verify returns False, when spatial dimensions have empty coordinates."""
    variable = xr.DataArray([1])

    assert get_dim_names_from_cf_standard_name_units(variable) == (None, None)

@pytest.mark.parametrize(
    "value_error_message, expected_handler",
    [
        (
            "Variable None has conflicting _FillValue (255) and missing_value (200). Cannot encode data.",
            apply_fillvalue_to_missing_value,
        ),
        (
            "Variable None has conflicting missing_value (200) and _FillValue (255). Cannot encode data.",
            apply_fillvalue_to_missing_value,
        ),
    ]
)
def test_get_value_error_handler_valid(input_datatree, value_error_message, expected_handler):
    """Test that known ValueError messages return the correct handler."""
    handler = get_value_error_handler(
        input_datatree,
        "group_five/variable_two",
        value_error_message
    )
    assert handler == expected_handler

@pytest.mark.parametrize(
    "variable_path, expected_fill, expected_missing",
    [
        ("group_five/variable_one", 355, 300),
        ("group_five/variable_two", 255, 200),
        ("group_one/group_two", None, None),
        ("group_six/variable_four", 255, 0),
    ]
)
def test_get_fillvalue_and_missing_value(input_datatree,
                                         variable_path,
                                         expected_fill,
                                         expected_missing
                                        ):
    """Test get_fillvalue_and_missing_value.  Verifies correct extraction of
       _FillValue and missing_value from encoding or attrs.
       Covers scenarios with missing metadata, malformed values,and identical attributes.

    """
    fill_value, missing_value = get_fillvalue_and_missing_value(input_datatree,
                                                                variable_path
                                                               )
    assert fill_value == expected_fill
    assert missing_value == expected_missing


def test_apply_fillvalue_to_missing_value(input_datatree):
    """Verifies that values matching missing_value are correctly
       replaced with _FillValue. Also checks that the missing_value
       attribute is removed and the process_note attribute is added.

    """
    expected_process_note = (
        '_FillValue = -999 represents all missing data including fill values'
        ' (orbit gaps, missing swaths) and other missing observations'
        ' originally marked as 999'
    )

    variable_data = apply_fillvalue_to_missing_value(
        input_datatree,
        "group_six/variable_one"
    )

    result = variable_data.values

    assert (result == np.array([[1, -999], [-999, 4]])).all()
    assert "missing_value" not in variable_data.encoding
    assert "missing_value" not in variable_data.attrs

    process_note = variable_data.attrs.get("process_note")
    assert process_note == expected_process_note

def test_apply_fillvalue_to_missing_value_no_missing_value_exception(input_datatree):
    """Ensures a ValueError exception if the missing_value attribute is absent

    """
    expected_exception = (
        "Missing _FillValue or missing_value attribute."
    )

    with pytest.raises(ValueError, match=expected_exception):
        apply_fillvalue_to_missing_value(
            input_datatree,
            "group_six/variable_two"
        )

def test_apply_fillvalue_to_missing_value_no_fillvalue_exception(input_datatree):
    """Ensures a ValueError exception if the _FillValue attribute is absent

    """
    expected_exception = (
        "Missing _FillValue or missing_value attribute."
    )

    with pytest.raises(ValueError, match=expected_exception):
        apply_fillvalue_to_missing_value(
            input_datatree,
            "group_six/variable_three"
        )

def test_rename_3d_dimensions(input_datatree_reorder_3d):
    """Ensure that a 3-dimensional array is rename to standard 'x'
    and 'y' to create the correct dimension order in a new DataTree

    """

    test_args = [
        [
            "Test rename (lat, lon, time) to (y, x, time)",
            "science_one",
            ("y", "x", "time"),
        ],
        [
            "Test reordered (latitude, longitude, time) to (y, x, time)",
            "group_one/science_two",
            ("y", "x", "time"),
        ],
        [
            "Test reordered (y-dim, x-dim, z-dim) to (y, x, z-dim)",
            "group_two/group_three/science_four",
            ("y", "x", "z-dim"),
        ],
        [
            "Test reordered (XDim, YDim, ZDim) to (x, y, ZDim)",
            "group_four/science_five",
            ("x", "y", "ZDim"),
        ],
    ]

    for description, variable_path, expected_path in test_args:
        print(description)
        variable_data = rename_dimensions(input_datatree_reorder_3d[variable_path])

        assert variable_data.dims == expected_path


@pytest.mark.parametrize(
    "description, variable_path, expected_value, "
    "expected_units, expected_dtype",
    [
        (
            "Testing days since",
            "group_one/time_days",
            2.0,
            "days since 2000-01-01 11:58:55.816Z",
            "datetime64[ns]",
        ),
        (
            "Testing hours since",
            "group_two/time_hours",
            12.0,
            "hours since 2000-01-01 11:58:55.816UTC",
            "datetime64[ns]",
        ),
        (
            "Testing minutes since",
            "group_three/time_minutes",
            30.0,
            "minutes since 2000-01-01 11:58:55.816Z",
            "datetime64[ns]",
        ),
        (
            "Testing seconds since",
            "group_four/time_seconds",
            45.0,
            "seconds since 2000-01-01 11:58:55.816ZUTC",
            "datetime64[ns]",
        ),
        (
            "Testing milliseconds since",
            "group_five/time_milliseconds",
            500.0,
            "milliseconds since 2000-01-01 11:58:55.816Z",
            "datetime64[ns]",
        ),
        (
            "Testing microseconds since",
            "group_six/time_microseconds",
            750.0,
            "microseconds since 2000-01-01 11:58:55.816UTC",
            "datetime64[ns]",
        ),
        (
            "Testing seconds without since",
            "group_seven/time_seconds",
            123.45,
            "2000-01-01 11:58:55",
            "float64",
        ),
    ],
)
def test_apply_datetime_conversion_all_units(
    input_datatree_datetime_units,
    description,
    variable_path,
    expected_value,
    expected_units,
    expected_dtype,
):
    """Verify datetime64[ns] variables convert to float64."""
    print(description)

    # Precondition: dtype before conversion
    assert (
        expected_dtype
        == input_datatree_datetime_units[variable_path].dtype
    )

    result = apply_datetime_conversion(
        input_datatree_datetime_units,
        variable_path,
    )

    # Units should be preserved
    assert result.attrs["units"] == expected_units

    # dtype should now be float
    assert result.dtype == np.float64

    assert np.float64(result.values) == expected_value
