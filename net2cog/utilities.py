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
    'latitude': ['degrees_north', 'degree_north', 'degree_N', 'degreeN', 'degreesN'],
    'longitude': ['degrees_east', 'degree_east', 'degree_E', 'degrees_E', 'degreeE', 'degreesE'],
}
DIM_STANDARD_NAME = {
    'x': ['projection_x_coordinate', 'projection_x_angular_coordinate', 'longitude'],
    'y': ['projection_y_coordinate', 'projection_y_angular_coordinate', 'latitude'],
}


class Net2CogError(Exception):
    """
    Exception raised when an error occurs while converting a NetCDF file to COG

    """

    def __init__(self, variable_name: str, error_message: str):
        super().__init__(
            f"Variable {variable_name} cannot be converted to tif: {error_message}"
        )


def reorder_dimensions(nc_xarray: xr.DataTree, variable_path: str) -> xr.DataArray:
    """This function reorders a 2D or 3D variable to create the correct
    dimension order, returning only the reordered variable as a DataArray.
    Originally this returned the whole DataTree, working with just the variable
    is a memory optimization.

    Parameters
    ----------
    nc_xarray : xarray.DataTree
        DataTree object representing the root group of the NetCDF-4 file.
    variable_path: str
        Variable path is present in DataTree

    Returns
    -------
    xr.DataArray
        New DataArray with proper dimension order

    """
    variable = nc_xarray[variable_path]

    x_dim, y_dim = get_dim_names_from_cf_standard_name_units(variable)

    if not x_dim and not y_dim:
        # Fallback: check against known coordinate sets
        x_dim = ",".join(set(X_COORDINATE) & set(variable.dims))
        y_dim = ",".join(set(Y_COORDINATE) & set(variable.dims))

    # Find the union of X_COORDINATE/Y_COORDINATE to variable.dims
    if not x_dim or not y_dim:
        raise Net2CogError(
            variable_path,
            f"{X_COORDINATE} or {Y_COORDINATE} dimensions not found in "
            f"variable.dims {variable.dims}",
        )

    # Subtract sets to isolate and retrieve the 3rd or 4th dimensions
    z_dim = list(set(variable.dims) - {x_dim, y_dim})
    if len(z_dim) > 1:
        # 4 Dimension and up not supported
        raise Net2CogError(
            variable_path,
            f"Only 2D and 3D data arrays supported. {variable.dims}",
        )

    if len(z_dim) == 0:
        # Reorder 2 Dimension
        return variable.transpose(y_dim, x_dim)

    if not z_dim or not z_dim[0]:
        raise Net2CogError(
            variable_path,
            f"{z_dim} dimensions not found in {variable.dims}",
        )

    # Reorder 3rd Dimension
    return variable.transpose(z_dim[0], y_dim, x_dim)


def rename_dimensions(variable: xr.DataArray) -> xr.DataArray:
    """This function renames coordinates to standard 'x' and 'y' required by
    rasterio, returning only the renamed variable as a DataArray.
    Originally the input and output were DataTree, but now both are DataArray as
    a memory optimization. The context where this is called is after
    reorder_dimension.

    Parameters
    ----------
    variable : xarray.DataArray
        DataArray object extracted from the original DataTree.

    Returns
    -------
    xr.DataArray
        New DataArray with renamed dimensions

    """
    x_dim, y_dim = get_dim_names_from_cf_standard_name_units(variable)

    if x_dim and y_dim:
        return variable.rename({y_dim: 'y', x_dim: 'x'})

    # Fallback: check against known coordinate sets
    x_dim = ",".join(set(X_COORDINATE) & set(variable.dims))
    y_dim = ",".join(set(Y_COORDINATE) & set(variable.dims))

    # Rename coordinates to standard 'x' and 'y' required by rasterio
    return variable.rename({y_dim: 'y', x_dim: 'x'})


def construct_variable_path(node_path: str, var_name: str) -> str:
    """Construct variable path from node path and variable name.

    Parameters
    ----------
    node_path : str
        Path of the node in the DataTree
    var_name : str
        Name of the variable

    Returns
    -------
    str
        Full variable path

    """
    if node_path == '/':
        return '/' + var_name
    return f"{node_path}/{var_name}"


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
    # issue/8: use subtree iterator instead of to_dict() to conserve memory
    for node in nc_xarray.subtree:
        if not (node.has_data and node.data_vars):
            continue

        for var_name in node.data_vars:
            var_name_str = str(var_name)
            var_path = construct_variable_path(node.path, var_name_str)

            if var_path == variable_path:
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
    """Ensure the variable has the required 2 or 3 dimensions,
    as 4-dimensional structures are not directly supported.

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
        True variables.shape >= 2 variables.shape < 4

    """
    if len(variable.shape) >= 2 and len(variable.shape) < 4:
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
    First attempt to check via CF-compliant standard_name/units
    Fallback is to check against known coordinate sets

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
        True if the variable has valid spatial dimensions
        False otherwise.

    """
    x_dim, y_dim = get_dim_names_from_cf_standard_name_units(variable)

    if x_dim and y_dim:
        return True

    # Fallback: check against known coordinate sets
    x_dim = ",".join(set(X_COORDINATE) & set(variable.dims))
    y_dim = ",".join(set(Y_COORDINATE) & set(variable.dims))

    if x_dim and y_dim:
        return True

    logger.info(
        "Unable to identify spatial dimensions from [%s] for variable: %s.\
        Skipping COG generation for this variable",
        variable.dims,
        variable_path,
    )

    return False


def get_dim_names_from_cf_standard_name_units(
    variable: xr.DataArray | xr.DataTree
) -> tuple[str | None, str | None]:
    """Get dimensions name from CF-compliant standard_name/units.

    Parameters
    ----------
    variable : xarray.DataArray | xarray.DataTree
        A variable within the NetCDF-4 file, as represented in xarray.

    Returns
    -------
    tuple: x_dim_name | None, y_dim_name | None

    """
    x_dim_name, y_dim_name = None, None

    for coord_name, coord in variable.coords.items():
        standard_name = coord.attrs.get('standard_name')
        units = coord.attrs.get('units')

        # Check for Y (Latitude or Y Projection)
        if not y_dim_name:
            if units in DIM_STANDARD_NAME_AND_UNITS.get('latitude', set()):
                y_dim_name = coord_name
            elif standard_name in DIM_STANDARD_NAME['y']:
                y_dim_name = coord_name

        # Check for X (Longitude or X Projection)
        if not x_dim_name:
            if units in DIM_STANDARD_NAME_AND_UNITS.get('longitude', set()):
                x_dim_name = coord_name
            elif standard_name in DIM_STANDARD_NAME['x']:
                x_dim_name = coord_name

    return x_dim_name, y_dim_name


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
    fill_value, missing_value = get_fillvalue_and_missing_value(
        nc_xarray, variable_path,
    )

    if (
        fill_value is not None
        and missing_value is not None
        and fill_value != missing_value
    ):
        return apply_fillvalue_to_missing_value

    raise ValueError(value_error_message)


def apply_fillvalue_to_missing_value(
        nc_xarray: xr.DataTree, variable_path: str
) -> xr.DataArray:
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
    xr.DataArray
        New DataArray with missing_value data replaced with _FillValue data,
        missing_value attribute deleted, and new process_note attribute
        to explain the process.

    """
    fill_value, missing_value = (
        get_fillvalue_and_missing_value(nc_xarray, variable_path)
    )

    if fill_value is None or missing_value is None:
        raise ValueError("Missing _FillValue or missing_value attribute.")

    # Extract the variable and copy only its values
    variable = nc_xarray[variable_path]
    values_tmp = variable.values.copy()

    # Replace all missing_value data with fill_value
    values_tmp[np.where(values_tmp == missing_value)] = fill_value

    # Create new DataArray with modified values using xarray constructor
    variable_modified = xr.DataArray(
        values_tmp,
        dims=variable.dims,
        coords=variable.coords,
        attrs=variable.attrs.copy(),
        name=variable.name
    )

    # Copy encoding but remove missing_value
    variable_modified.encoding.update(variable.encoding)
    if 'missing_value' in variable_modified.encoding:
        del variable_modified.encoding['missing_value']
    if 'missing_value' in variable_modified.attrs:
        del variable_modified.attrs['missing_value']

    # Add process_note attribute that explains this processing
    process_note = (f"_FillValue = {fill_value} represents all missing "
                    f"data including fill values (orbit gaps, missing swaths) "
                    f"and other missing observations originally marked "
                    f"as {missing_value}")

    variable_modified.attrs["process_note"] = process_note

    return variable_modified


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
