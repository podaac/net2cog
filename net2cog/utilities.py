"""
=========
utilties.py
=========

Utility functions for use within the net2cog service.
"""

import xarray as xr

X_COORDINATE = ("lon", "longitude", "x", "x-dim")
Y_COORDINATE = ("lat", "latitude", "y", "y-dim")


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
    x_dim = "".join(dim for dim in X_COORDINATE if dim in nc_xarray[variable_path].dims)
    y_dim = "".join(dim for dim in Y_COORDINATE if dim in nc_xarray[variable_path].dims)

    extra_dim = tuple(set(list(nc_xarray[variable_path].dims)) - {x_dim, y_dim})
    if len(extra_dim) > 1:
        raise Net2CogError(
            variable_path,
            f"Only 2D and 3D data arrays supported. {nc_xarray[variable_path].dims}",
        )

    # DataTree nc_xarray is immutable so copy new DataTree to reorder dimensions
    nc_xarray_tmp = nc_xarray.copy()

    # Reorder 3rd Dimension
    if len(extra_dim) == 1:
        # Find the difference between two sets
        z_dim = "".join(set(nc_xarray[variable_path].dims) - {x_dim, y_dim})

        if None in [x_dim, y_dim, z_dim]:
            raise Net2CogError(
                variable_path,
                f"{x_dim}, {y_dim}, or {z_dim} dimensions not found in DataTree {nc_xarray[variable_path].dims}",
            )

        nc_xarray_tmp[variable_path] = nc_xarray[variable_path].transpose(
            z_dim, y_dim, x_dim
        )
    else:
        # Reorder 2 Dimension
        nc_xarray_tmp[variable_path] = nc_xarray[variable_path].transpose(y_dim, x_dim)

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
