# pylint: disable=line-too-long
# flake8: noqa: E501

"""
================
netcdf_convert_harmony.py
================

Implementation of harmony-service-lib that invokes the netcdf converter.
"""
import argparse
import json
import os
import pathlib
import shutil
import tempfile
from os.path import basename, splitext

import harmony_service_lib
import pystac
from harmony_service_lib import BaseHarmonyAdapter
from harmony_service_lib.exceptions import HarmonyException
from harmony_service_lib.message import Source
from harmony_service_lib.util import download, generate_output_filename, stage
from pystac import Asset, Item

from net2cog import netcdf_convert
from net2cog.netcdf_convert import Net2CogError

DATA_DIRECTORY_ENV = "DATA_DIRECTORY"


class NetcdfConverterService(BaseHarmonyAdapter):
    """
    See https://github.com/nasa/harmony-service-lib-py
    for documentation and examples.
    """

    def __init__(self, message, catalog=None, config=None):
        super().__init__(message, catalog, config)

        self.data_dir = os.getenv(DATA_DIRECTORY_ENV, '/home/dockeruser/data')
        pathlib.Path(self.data_dir).mkdir(parents=True, exist_ok=True)

        # Create temp directory
        self.job_data_dir = tempfile.mkdtemp(prefix=message.requestId, dir=self.data_dir)

    def process_item(self, item: pystac.Item, source: Source) -> pystac.Item:
        """
        Performs net2cog on input STAC Item's data, returning
        an output STAC item

        Parameters
        ----------
        item : pystac.Item
            the item that should be coggified
        source : harmony_service_lib.message.Source
            the input source defining the item

        Returns
        -------
        pystac.Item
            a STAC item describing the output
        """
        output_dir = self.job_data_dir
        try:
            self.logger.info('Input item: %s', json.dumps(item.to_dict()))
            self.logger.info('Input source: %s', source)
            # Get the data file
            asset = next(v for k, v in item.assets.items() if 'data' in (v.roles or []))
            self.logger.info('Downloading %s to %s', asset.href, output_dir)
            input_filename = download(
                asset.href,
                output_dir,
                logger=self.logger,
                access_token=self.message.accessToken,
                cfg=self.config
            )

            # Determine variables that need processing
            var_list = source.process('variables')

            if var_list:
                var_list = list(map(lambda var: var.name, var_list))
                self.logger.info('Processing variables %s', var_list)
            else:
                self.logger.info('Processing all variables.')

            # Run the netcdf converter for the complete netcdf granule
            try:
                generated_cogs = netcdf_convert.netcdf_converter(
                    pathlib.Path(input_filename),
                    pathlib.Path(output_dir),
                    var_list,
                    self.logger,
                )
            except Net2CogError as error:
                raise HarmonyException(
                    f'net2cog failed to convert {asset.title}: {error}') from error
            except Exception as uncaught_exception:
                raise HarmonyException(str(f'Uncaught error in net2cog. '
                                           f'Notify net2cog service provider. '
                                           f'Message: {uncaught_exception}')) from uncaught_exception

            return self.stage_output_and_create_output_stac(
                basename(asset.href),
                generated_cogs,
                item
            )
        finally:
            # Clean up any intermediate resources
            shutil.rmtree(self.job_data_dir)

    def stage_output_and_create_output_stac(
        self,
        source_asset_basename: str,
        output_files: list[str],
        input_stac_item: Item
    ) -> Item:
        """Iterate through all generated COGs and stage the results in S3. Also
        add a unique pystac.Asset for each COG to the pystac.Item returned to
        Harmony.

        Parameters
        ----------
        output_files : list[str]
            the file names of generated COGs to be staged. It is assumed that
            the file names adhere to the convention of `<variable_name>.tif`.
        input_stac_item : pystac.Item
            the input STAC for the request. This is the basis of the output
            STAC, which will replace the pystac.Assets with generated COGs.

        Returns
        -------
        pystac.Item
            a STAC item describing the output. If there are multiple variables,
            this STAC item will have multiple assets.

        """

        output_stac_item = input_stac_item.clone()
        output_stac_item.assets = {}

        for output_file in output_files:
            output_basename = generate_output_filename(
                source_asset_basename,
                ext='tif',
                variable_subset=[splitext(basename(output_file))[0]],
                is_reformatted=True,
            )

            staged_url = stage(
                output_file,
                output_basename,
                pystac.MediaType.COG,
                location=self.message.stagingLocation,
                logger=self.logger,
                cfg=self.config
            )
            self.logger.info('Staged %s to %s', output_file, staged_url)

            # Each asset needs a unique key, so the filename of the COG is used
            output_stac_item.assets[output_basename] = Asset(
                staged_url,
                title=output_basename,
                media_type=pystac.MediaType.COG,
                roles=['visual'],
            )

        return output_stac_item


def main():
    """Parse command line arguments and invoke the service to respond to
    them.

    Returns
    -------
    None

    """
    parser = argparse.ArgumentParser(prog='net2cog_harmony',
                                     description='Run the netcdf converter service')
    harmony_service_lib.setup_cli(parser)
    args = parser.parse_args()
    if harmony_service_lib.is_harmony_cli(args):
        harmony_service_lib.run_cli(parser, args, NetcdfConverterService)
    else:
        parser.error("Only --harmony CLIs are supported")
