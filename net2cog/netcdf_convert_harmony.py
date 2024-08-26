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

import harmony
import pystac
from harmony.exceptions import HarmonyException
from pystac import Asset

from net2cog import netcdf_convert

DATA_DIRECTORY_ENV = "DATA_DIRECTORY"


class NetcdfConverterService(harmony.BaseHarmonyAdapter):
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

    def process_item(self, item: pystac.Item, source: harmony.message.Source) -> pystac.Item:
        """
        Performs net2cog on input STAC Item's data, returning
        an output STAC item

        Parameters
        ----------
        item : pystac.Item
            the item that should be coggified
        source : harmony.message.Source
            the input source defining the item

        Returns
        -------
        pystac.Item
            a STAC item describing the output
        """
        result = item.clone()
        result.assets = {}
        output_dir = self.job_data_dir

        self.logger.info('Input item %s', json.dumps(item.to_dict()))
        try:
            # Get the data file
            asset = next(v for k, v in item.assets.items() if 'data' in (v.roles or []))
            self.logger.info('Downloading %s to %s', asset.href, output_dir)
            input_filename = harmony.adapter.util.download(asset.href,
                                                           output_dir,
                                                           logger=self.logger,
                                                           access_token=self.message.accessToken,
                                                           cfg=self.config)

            # Generate output filename
            output_filename, output_file_ext = os.path.splitext(
                harmony.adapter.util.generate_output_filename(input_filename, ext='tif'))
            output_filename = f'{output_filename}_converted{output_file_ext}'

            # Determine variables that need processing
            self.logger.info('Generating COG(s) for %s output will be saved to %s', input_filename, output_filename)
            var_list = source.process('variables')
            if not isinstance(var_list, list):
                var_list = [var_list]
            if len(var_list) > 1:
                raise HarmonyException(
                    'net2cog harmony adapter currently only supports processing one variable at a time. '
                    'Please specify a single variable in your Harmony request.')
            var_list = list(map(lambda var: var.name, var_list))
            self.logger.info('Processing variables %s', var_list)

            # Run the netcdf converter for the complete netcdf granule
            cog_generated = next(iter(netcdf_convert.netcdf_converter(pathlib.Path(input_filename),
                                                                      pathlib.Path(output_dir).joinpath(
                                                                          output_filename),
                                                                      var_list=var_list)), [])

            # Stage the output file with a conventional filename
            self.logger.info('Generated COG %s', cog_generated)
            staged_filename = os.path.basename(cog_generated)
            url = harmony.adapter.util.stage(cog_generated,
                                             staged_filename,
                                             pystac.MediaType.COG,
                                             location=self.message.stagingLocation,
                                             logger=self.logger,
                                             cfg=self.config)
            self.logger.info('Staged %s to %s', cog_generated, url)

            # Update the STAC record
            result.assets['visual'] = Asset(url, title=staged_filename, media_type=pystac.MediaType.COG,
                                            roles=['visual'])

            # Return the STAC record
            self.logger.info('Processed item %s', json.dumps(result.to_dict()))
            return result
        except Exception as uncaught_exception:
            raise HarmonyException(str(f'Uncaught error in net2cog. '
                                       f'Notify net2cog service provider. '
                                       f'Message: {uncaught_exception}')) from uncaught_exception
        finally:
            # Clean up any intermediate resources
            shutil.rmtree(self.job_data_dir)


def main():
    """Parse command line arguments and invoke the service to respond to
    them.

    Returns
    -------
    None

    """
    parser = argparse.ArgumentParser(prog='net2cog_harmony',
                                     description='Run the netcdf converter service')
    harmony.setup_cli(parser)
    args = parser.parse_args()
    if harmony.is_harmony_cli(args):
        harmony.run_cli(parser, args, NetcdfConverterService)
    else:
        parser.error("Only --harmony CLIs are supported")
