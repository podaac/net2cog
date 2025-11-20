"""
=========
utilties.py
=========

Utility functions for use within the net2cog service.
"""

from logging import Logger
from collections.abc import Callable
import xarray as xr
import numpy as np

X_COORDINATE = ("lon", "longitude", "x", "x-dim", "XDim")
Y_COORDINATE = ("lat", "latitude", "y", "y-dim", "YDim")
DTYPE_SUPPORTED = [
    'ubyte',
    'uint8',
    'uint16',
    'int16',
    'uint32',
    'int32',
    'float32',
    'float64',
]
DIM_STANDARD_NAME_AND_UNITS = {
    'projection_x_coordinate': ['m', 'meters', 'meter'],
    'projection_y_coordinate': ['m', 'meters', 'meter'],
    'projection_x_angular_coordinate': ['m', 'meters', 'meter'],
    'projection_y_angular_coordinate': ['m', 'meters', 'meter'],
    'latitude': ['degrees_north', 'degree_north', 'degree_N', 'degreeN', 'degreesN'],
    'longitude': ['degrees_east', 'degree_east', 'degree_E', 'degrees_E', 'degreeE', 'degreesE'],
}


class Net2CogError(Exception):
    """
    Exception raised when an error occurs while converting a NetCDF file to COG

    """

    def __init__(self, variable_name: str, error_message: str):
        super().__init__(
            f"Variable {variable_name} cannot be converted to tif: {error_message}"
        )


def reorder_dimensions(nc_xarray: xr.DataTree, variable_path: str) -> xr.DataTree:
    """This function reorders a 2D and 3D using DataTree.transpose() to
    create the correct dimension order in a new DataTree.

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.
    variable_path: str
        Variable path is present in DataTree

    Returns
    -------
    xr.DataTree
        New DataTree with proper order dimensions

    """
    # Find the union of X_COORDINATE/Y_COORDINATE to DataTree.dims
    x_dim = list(set(X_COORDINATE) & set(nc_xarray[variable_path].dims))
    y_dim = list(set(Y_COORDINATE) & set(nc_xarray[variable_path].dims))
    if not x_dim or not y_dim:
        raise Net2CogError(
            variable_path,
            f"{X_COORDINATE} or {Y_COORDINATE} dimensions not found in "
            f"DataTree.dims {nc_xarray[variable_path].dims}",
        )

    z_dim = list(set(nc_xarray[variable_path].dims) - {x_dim[0], y_dim[0]})
    if len(z_dim) > 1:
        # 4 Dimension and up not supported
        raise Net2CogError(
            variable_path,
            f"Only 2D and 3D data arrays supported. {nc_xarray[variable_path].dims}",
        )

    # DataTree nc_xarray is immutable so copy new DataTree to reorder dimensions
    nc_xarray_tmp = nc_xarray.copy()

    if len(z_dim) == 0:
        # Reorder 2 Dimension
        nc_xarray_tmp[variable_path] = nc_xarray[variable_path].transpose(
            y_dim[0], x_dim[0]
        )
    else:
        # Reorder 3rd Dimension
        if not z_dim or not z_dim[0]:
            raise Net2CogError(
                variable_path,
                f"{z_dim} dimensions not found in {nc_xarray[variable_path].dims}",
            )

        nc_xarray_tmp[variable_path] = nc_xarray[variable_path].transpose(
            z_dim[0], y_dim[0], x_dim[0]
        )

    return nc_xarray_tmp


def is_variable_in_datatree(nc_xarray: xr.DataTree, variable_path: str) -> bool:
    """Traverse tree and verify variables path in DataTree.

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.
    variable_path: str
        Variable path is present in DataTree

    Returns
    -------
    bool
        True if variables in DataTree
        False if variables not in DataTree

    """
    data_variables = []
    for group_path, group in nc_xarray.to_dict().items():
        data_variables.extend(
            [
                "/".join([group_path.rstrip("/"), str(data_var)])
                for data_var in group.data_vars
            ]
        )

        if variable_path in data_variables:
            return True

    return False


def resolve_relative_path(
    nc_xarray: xr.DataTree,
    variable_path: str,
    reference_path: str,
) -> str:
    """Given a relative path within a granule, resolve an absolute path given
    the location of the variable making the reference. For example, a
    variable might refer to a grid_mapping variable, or a coordinate
    variable in the CF-Convention metadata attributes.

    Finally, the resolved path is checked, to ensure it exists in the
    DataTree. If not retrun None.

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        xarray DataTree loaded from NetCDF file. This represents the whole
        file.
    variable_path: str
        Full of the variable within the file to convert.
    reference_path: str
        Path of the reference (grid_mapping) attribute
    logger : logging.Logger
        Python Logger object for emitting log messages.

    Returns
    -------
    str
        Returns a path to reference attribute else None

    """

    # Extract the group of a variable from the full path,
    # e.g. '/this/is/my/variable' should return '/this/is/my':
    group_path = variable_path.rpartition("/")[0]

    if reference_path.startswith("../"):
        # Reference is relative, and requires manipulation
        resolved_path = construct_absolute_path(group_path, reference_path)
    elif reference_path.startswith("/"):
        # Reference is already absolute
        resolved_path = reference_path
    elif reference_path.startswith("./"):
        # Reference is in the same group as this variable
        resolved_path = group_path + reference_path[1:]
    elif reference_path in nc_xarray[group_path].data_vars:
        # Reference is in the same group as this variable
        resolved_path = "/".join([group_path, reference_path])
    elif is_variable_in_datatree(nc_xarray, f"/{reference_path}"):
        resolved_path = f"/{reference_path}"
    else:
        raise Net2CogError(
            variable_path,
            f"Variable {variable_path} grid_mapping or coordinate: "
            "{reference_path} relative path has incorrect nesting",
        )

    return resolved_path


def construct_absolute_path(group_path: str, reference: str) -> str:
    """For a relative reference to another variable (e.g. '../latitude'),
    construct an absolute path by combining the reference with the
    group path of the variable.

    """
    relative_prefix = "../"
    group_path_pieces = group_path.split("/")

    while reference.startswith(relative_prefix):
        reference = reference[len(relative_prefix):]
        group_path_pieces.pop()

    absolute_path = group_path_pieces + [reference]
    return "/".join(absolute_path)


def is_valid_shape(
    variable: xr.DataArray | xr.DataTree, variable_path: str, logger: Logger
) -> bool:
    """Ensure variable has required dimensions.

    Parameters
    ----------
    variable : xarray.DataArray | xarray.DataTree
        A variable within the NetCDF-4 file, as represented in xarray.
    variable_path: str
        Full of the variable within the file to convert.
    logger : logging.Logger
        Python Logger object for emitting log messages.

    Returns
    -------
    bool
        False variables.shape < 2
        True variables.shape >= 2

    """
    if len(variable.shape) >= 2:
        return True

    logger.info(
        "Invalid shape %s for variable: %s. Skipping COG generation for this variable",
        variable.shape,
        variable_path,
    )

    return False


def is_valid_dtype(
    variable: xr.DataArray | xr.DataTree, variable_path: str, logger: Logger
) -> bool:
    """Ensure variable has required dtype.

    Parameters
    ----------
    variable : xarray.DataArray | xarray.DataTree
        A variable within the NetCDF-4 file, as represented in xarray.
    variable_path: str
        Full of the variable within the file to convert.
    logger : logging.Logger
        Python Logger object for emitting log messages.

    Returns
    -------
    bool
        False variables.dtype is string (S1|S2)
        True variables.dtype is ubyte|int|float

    """
    if variable.dtype.name in DTYPE_SUPPORTED:
        return True

    logger.info(
        "Invalid dtype %s for variable: %s. Skipping COG generation for this variable",
        variable.dtype,
        variable_path,
    )

    return False


def is_valid_spatial_dimensions(
    variable: xr.DataArray | xr.DataTree, variable_path: str, logger: Logger
) -> bool:
    """Ensure variable has required spatial dimensions.
    Convert the string to lowercase before performing the comparison

    Parameters
    ----------
    variable : xarray.DataArray | xarray.DataTree
        A variable within the NetCDF-4 file, as represented in xarray.
    variable_path: str
        Full of the variable within the file to convert.
    logger : logging.Logger
        Python Logger object for emitting log messages.

    Returns
    -------
    bool
        Value denoting if the variable has dimensions including one of the
        following sets of spatial dimension names:

            * {"lon", "lat"}
            * {"longitude", "latitude"}
            * {"x", "y"}
            * {"x-dim", "y-dim"}
            * {"XDim", "YDim"}  (Convert to lowercase before compare)

    """
    variable_dims = [dim.lower() for dim in variable.dims]
    if (
        {"lon", "lat"}.issubset(set(variable_dims))
        or {"longitude", "latitude"}.issubset(set(variable_dims))
        or {"x", "y"}.issubset(set(variable_dims))
        or {"x-dim", "y-dim"}.issubset(set(variable_dims))
        or {"xdim", "ydim"}.issubset(set(variable_dims))
    ):
        return True

    # Fallback: check CF-compliant standard_name and units
    if not is_valid_spatial_dimensions_with_standard_name_units(
        variable,
        variable_path,
        logger
    ):
        logger.info(
            "Unable to identify spatial dimensions from [%s] for variable: %s.\
            Skipping COG generation for this variable",
            variable.dims,
            variable_path,
        )

        return False

    return True


def is_valid_spatial_dimensions_with_standard_name_units(
    variable: xr.DataArray | xr.DataTree, variable_path: str, logger: Logger
) -> bool:
    """Ensure spatial dimensions have valid CF-compliant standard_name and units.

    Parameters
    ----------
    variable : xarray.DataArray | xarray.DataTree
        A variable within the NetCDF-4 file, as represented in xarray.
    variable_path: str
        Full of the variable within the file to convert.
    logger : logging.Logger
        Python Logger object for emitting log messages.

    Returns
    -------
    bool
        True: True if all coordinate dimensions have valid standard_name and units.
        False: otherwise.

    """
    if not variable.coords:
        return False

    for coord_name, coord in variable.coords.items():
        standard_name = coord.attrs.get('standard_name')
        units = coord.attrs.get('units')

        if standard_name is None or units is None:
            return False

        if standard_name not in DIM_STANDARD_NAME_AND_UNITS:
            logger.info(
                "The standard_name [%s] for coordinate [%s] in variable: %s \
                do not comply with the CF (Climate and Forecast) conventions",
                standard_name,
                coord_name,
                variable_path,
            )
            return False

        if units not in DIM_STANDARD_NAME_AND_UNITS.get(standard_name, set()):
            logger.info(
                "The units [%s] for coordinate [%s] in variable: %s \
                do not comply with the CF (Climate and Forecast) conventions",
                units,
                coord_name,
                variable_path,
            )
            return False

    return True


def get_value_error_handler(
        nc_xarray: xr.DataTree, variable_path: str, value_error_message: str,
) -> Callable:
    """ This function returns the appropriate handler method
    based on the ValueError message.  Raises a ValueError if
    no matching handler is found.

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.
    variable_path: str
        Variable path is present in DataTree
    value_error_message: str
        The ValueError exception message

    Returns
    -------
        Callable: Returns the right callable method
        apply_fillvalue_to_missing_value()
        or any other process.

    """
    # ValueError: Variable None has conflicting _FillValue (255) and
    # missing_value (200).  Cannot encode data.
    fill_missing_value_keywords = ['_FillValue', 'missing_value']

    if all(word in value_error_message for word in fill_missing_value_keywords):
        fill_value, missing_value = get_fillvalue_and_missing_value(
            nc_xarray, variable_path,
        )

        if fill_value is not None and missing_value is not None and fill_value != missing_value:
            return apply_fillvalue_to_missing_value

    raise ValueError(value_error_message)


def apply_fillvalue_to_missing_value(
        nc_xarray: xr.DataTree, variable_path: str
) -> xr.DataTree:
    """This function replaces occurrences of missing_value in the variable's
    data array with _FillValue. It also removes the missing_value attribute
    and adds a new process_note attribute to document the transformation
    for reference.

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.
    variable_path: str
        Variable path is present in DataTree

    Returns
    -------
    xr.DataTree
        New DataTree with missing_value data replace with _FillValue data,
        missing_value attribute delete, and new process_note attribute
        to explain the process.

    """
    fill_value, missing_value = (
        get_fillvalue_and_missing_value(nc_xarray, variable_path)
    )

    if fill_value is None or missing_value is None:
        raise ValueError("Missing _FillValue or missing_value attribute.")

    # DataTree nc_xarray is immutable so copy new DataTree
    # to change missing_value data
    nc_xarray_tmp = nc_xarray.copy()
    values_tmp = nc_xarray_tmp[variable_path].values.copy()

    # Replace all missing_value data with fill_value
    values_tmp[np.where(values_tmp == missing_value)] = fill_value

    # Assign updated values back to the DataTree
    nc_xarray_tmp[variable_path].values = values_tmp

    # Delete missing_value
    if 'missing_value' in nc_xarray_tmp[variable_path].encoding:
        del nc_xarray_tmp[variable_path].encoding['missing_value']
    if 'missing_value' in nc_xarray_tmp[variable_path].attrs:
        del nc_xarray_tmp[variable_path].attrs['missing_value']

    # Add process_note attribute that explains this processing
    process_note = (f"_FillValue = {fill_value} represents all missing "
                    f"data including fill values (orbit gaps, missing swaths) "
                    f"and other missing observations originally marked "
                    f"as {missing_value}")

    nc_xarray_tmp[variable_path].attrs["process_note"] = process_note

    return nc_xarray_tmp


def get_fillvalue_and_missing_value(
        nc_xarray: xr.DataTree, variable_path: str
) -> tuple[
    np.uint | np.floating | None,
    np.uint | np.floating | None
]:
    """
    Determine the appropriate _FillValue and missing_value for a given variable.

    The search order for each attribute is:
      - encoding['_FillValue']
      - attrs['_FillValue']
      - encoding['missing_value']
      - attrs['missing_value']

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.
    variable_path: str
        Variable path is present in DataTree

    Returns
    -------
        tuple[np.uint | np.floating | None,
              np.uint | np.floating | None];
        A tuple containing the _FillValue and missing_value or None.

    """
    fill_value = nc_xarray[variable_path].encoding.get("_FillValue")
    if fill_value is None:
        fill_value = nc_xarray[variable_path].attrs.get('_FillValue')

    missing_value = nc_xarray[variable_path].encoding.get("missing_value")
    if missing_value is None:
        missing_value = nc_xarray[variable_path].attrs.get("missing_value")

    return fill_value, missing_value
