"""
=========
utilties.py
=========

Utility functions for use within the net2cog service.
"""

from logging import Logger
import xarray as xr

X_COORDINATE = ("lon", "longitude", "x", "x-dim")
Y_COORDINATE = ("lat", "latitude", "y", "y-dim")
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

    """
    if (
        {"lon", "lat"}.issubset(set(variable.dims))
        or {"longitude", "latitude"}.issubset(set(variable.dims))
        or {"x", "y"}.issubset(set(variable.dims))
        or {"x-dim", "y-dim"}.issubset(set(variable.dims))
    ):
        return True

    logger.info(
        "Unable to identify spatial dimensions from [%s] for variable: %s. Skipping COG generation for this variable",
        variable.dims,
        variable_path,
    )

    return False
