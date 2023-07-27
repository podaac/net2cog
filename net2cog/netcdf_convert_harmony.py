# pylint: disable=line-too-long
# flake8: noqa: E501

"""
================
netcdf_convert_harmony.py
================

Implementation of harmony-service-lib that invokes the netcdf converter.
"""
import argparse
import os
import pathlib

import harmony

from net2cog import netcdf_convert

DATA_DIRECTORY_ENV = "DATA_DIRECTORY"


class NetcdfConverterService(harmony.BaseHarmonyAdapter):
    """
    See https://github.com/nasa/harmony-service-lib-py
    for documentation and examples.
    """

    def __init__(self, message):
        super().__init__(message)

        self.data_dir = os.getenv(DATA_DIRECTORY_ENV, '/home/dockeruser/data')
        self.job_data_dir = os.path.join(self.data_dir, message.requestId)
        # Create temp directory
        pathlib.Path(self.job_data_dir).mkdir(parents=True, exist_ok=True)

    def invoke(self):
        """Run the service on the message contained in `self.message`.
        Fetches data, runs the service, puts the result in a file,
        calls back to Harmony, and cleans up after itself.
        """

        logger = self.logger
        message = self.message

        logger.info("Received message %s", message)

        try:
            # Limit to the first granule.  See note in method documentation
            granules = message.granules
            if message.isSynchronous:
                granules = granules[:1]

            for i, granule in enumerate(granules):
                self.download_granules([granule])

                self.logger.info('local_filename = %s', granule.local_filename)
                directory_name = os.path.splitext(os.path.basename(granule.local_filename))[0]
                output_file_directory = os.path.join(self.job_data_dir,
                                                     f'converted_{directory_name}')
                output_filename = f'{output_file_directory}/' \
                                  f'{os.path.basename(granule.name)}'
                self.logger.debug('output: %s', output_filename)

                # Run the netcdf converter for the complete netcdf granule
                cogs_generated = netcdf_convert.netcdf_converter(
                    granule.local_filename, output_filename
                )
                current_progress = int(100 * i / len(granules))
                next_progress = int(100 * (i+1) / len(granules))
                for cog in cogs_generated:
                    if message.isSynchronous:
                        self.completed_with_local_file(
                            cog,
                            remote_filename=os.path.basename(cog),
                            mime="tiff"
                        )
                    else:
                        self.async_add_local_file_partial_result(
                            cog,
                            remote_filename=os.path.basename(cog),
                            title=granule.id,
                            progress=current_progress if cog != cogs_generated[-1] else next_progress,
                            mime="tiff"
                        )
            if not message.isSynchronous:
                self.async_completed_successfully()

        except Exception as ex:  # pylint: disable=W0703
            logger.exception(ex)
            self.completed_with_error('An unexpected error occurred')
        finally:
            self.cleanup()


def main():
    """Parse command line arguments and invoke the service to respond to
    them.

    Returns
    -------
    None

    """
    parser = argparse.ArgumentParser(prog='podaac-netcdf-converter',
                                     description='Run the netcdf converter service')
    harmony.setup_cli(parser)
    args = parser.parse_args()
    if harmony.is_harmony_cli(args):
        harmony.run_cli(parser, args, NetcdfConverterService)
    else:
        parser.error("Only --harmony CLIs are supported")
