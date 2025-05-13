"""
=========
utilties.py
=========

Utility functions for use within the net2cog service.
"""

from logging import Logger

import xarray as xr


def resolve_relative_path(
    nc_xarray: xr.DataTree,
    variable_path: str,
    reference_path: str,
    logger: Logger,
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
    split_full_path = variable_path.split("/")
    split_full_path.pop(-1)

    group_path = "/".join(split_full_path) or None

    if group_path is not None:
        reference_path = reference_path.rstrip(":")

        if reference_path.startswith("../"):
            # Reference is relative, and requires manipulation
            resolved_path = construct_absolute_path(group_path, reference_path)
        elif reference_path.startswith("/"):
            # Reference is already absolute
            resolved_path = reference_path
        elif reference_path.startswith("./"):
            # Reference is in the same group as this variable
            resolved_path = group_path + reference_path[1:]
        else:
            # Reference is in the same group as this variable
            absolute_path = "/".join([group_path, reference_path])

            try:
                if nc_xarray[absolute_path] is not None:
                    resolved_path = absolute_path
            except KeyError:
                resolved_path = f"/{reference_path}"
    else:
        reference_path = reference_path.rstrip(":")

        if reference_path.startswith("/"):
            resolved_path = reference_path
        else:
            resolved_path = f"/{reference_path}"

    try:
        if nc_xarray[resolved_path] is not None:
            logger.info(
                "Variable %s grid_mapping or coordinate: Resolved path %s",
                variable_path,
                resolved_path,
            )
    except KeyError:
        logger.info(
            "Variable %s grid_mapping or coordinate: %s relative path has incorrect nesting",
            variable_path,
            reference_path,
        )
        resolved_path = None

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
