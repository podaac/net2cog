# pylint: disable=unused-import
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
    reference_location = variable_path.rpartition("/")[0]

    if reference_path.startswith("/"):
        # If the path starts with a slash, assume it is absolute
        resolved_path = reference_path
    else:
        # If a path doesn't indicate nesing, first check if there is a variable
        # matching the name in the same group as the referee, otherwise assume
        # the variable reference is from the root group.
        reference_in_group = "/".join([reference_location, reference_path])

        try:
            # Attempts to access the variable, catches the exception if it does not exist
            nc_xarray[reference_in_group]
            resolved_path = reference_in_group
        except KeyError:
            resolved_path = f"/{reference_path}"

    try:
        # Attempts to access the variable, catches the exception if it does not exist
        nc_xarray[resolved_path]
        logger.info(
            "Variable %s grid_mapping or coordinate: resolved path %s",
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
