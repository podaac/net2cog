"""
================
netcdf_convert_worker.py
================

NetCDF convert worker which, when a message on the queue is retrieved, runs the
NetCDF converter.
"""
import logging
import os
from os.path import join, exists
from urllib.parse import urlparse

from podaac.baseworker.worker_base import DecoratedWorkerBase, \
    worker_process, JobState, JobFailedException
from podaac.netcdf_converter import netcdf_convert


class NCWorker(DecoratedWorkerBase):
    """
    NCWorker is an instantiation of the WorkerBase class. All that
    *needs* to be implemented here is the "process" command which takes
    a service-message compliant json object. All work should be done in
    this command using any modules or sub modules you need. The files
    should be locally staged already in /data/{message["identifier"]/}

    If a resulting file is output, write it to
    /data/{message["identifier"]/fileName, and return this string (or
    list of strings for multiple files)
    """

    def __init__(self, queue_name):
        self.queue_name = queue_name
        self.log_level = logging.DEBUG
        super().__init__(queue_name)

    @worker_process(pre_job_state=JobState.INPUT_STAGED, post_job_state=JobState.PROCESSED)
    def process(self, message):
        """
        This function is called when the services retrieves a message
        on the queue.

        Parameters
        ----------
        message : dict
            The message from the queue

        Returns
        -------
        list of strings
            A list of output files
        """
        logging.info("NCWorker NetCDF Converter process")
        logging.info("Processing job: %s", message["identifier"])
        logging.debug(message)

        output_dir = os.path.join(self.data_dir, message["identifier"])
        if not exists(output_dir):
            os.makedirs(output_dir)

        local_files = [urlparse(f).path for f in message["meta"]["processedFiles"]]

        output_file_paths = [join(output_dir, "netcdf_converted_{}"
                                  .format(os.path.basename(urlparse(file).path)))
                             for file in local_files]

        all_cog_outpaths = []
        for input_file, output_file in zip(local_files, output_file_paths):
            logging.info("input: %s", input_file)
            logging.info("output: %s", output_file)

            try:
                # message metadata settings to be used to specify parameters in the COG conversion
                # user specified variables for conversion
                if 'meta' in message.keys():
                    meta = message['meta']
                    if 'nc_vars' in meta.keys():
                        msg_vars = message['meta']['nc_vars']
                        var_list = msg_vars.split(", ")
                        var_list.sort()

                        # Run the netcdf converter for variable selection
                        cogs_generated = netcdf_convert.netcdf_converter(
                            input_file, output_file, var_list
                        )
                        logging.info("NC Var Process output: %s", cogs_generated)
                        for cog in cogs_generated:
                            all_cog_outpaths.append(cog)
                    else:
                        # Run the netcdf converter for the complete netcdf
                        logging.info("META found but no variables specified, "
                                     "running complete NetCDF file: %s", input_file)
                        cogs_generated = netcdf_convert.netcdf_converter(input_file, output_file)
                        logging.info("Complete NetCDF Process output: %s", cogs_generated)
                        for cog in cogs_generated:
                            all_cog_outpaths.append(cog)

                else:
                    # Run the netcdf converter for the complete netcdf
                    logging.info("NetCDF variables not specified, "
                                 "running complete NetCDF file: %s", input_file)
                    cogs_generated = netcdf_convert.netcdf_converter(input_file, output_file)
                    logging.info("Complete NetCDF Process output: %s", cogs_generated)
                    for cog in cogs_generated:
                        all_cog_outpaths.append(cog)

                # # Rename result to remove .tmp
                # os.rename("{}.tmp".format(output_file), output_file)
            except (FileNotFoundError, ValueError) as error:
                error_message = f'NetCDF failed on {os.path.basename(input_file)}: {str(error)}'
                logging.error(error_message)
                raise JobFailedException(error_message) from error

        logging.info("Process output: %s", all_cog_outpaths)
        return all_cog_outpaths


def main():
    """
    Entry point to the NetCDF Converter Service. This function should be called
    to start the worker.
    """

    root_log_level = os.environ.get('WORKER_ROOT_LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(level=root_log_level)

    service_log_level = os.environ.get('WORKER_SERVICE_LOG_LEVEL', 'INFO').upper()
    logger = logging.getLogger("podaac")
    logger.setLevel(service_log_level)

    queue = "service-NC-queue"
    if 'QUEUE_NAME' in os.environ:
        queue = os.environ["QUEUE_NAME"]

    logging.info("Starting NCWorker for NetCDF Converter using queue: %s", queue)
    NCWorker(str(queue)).run()


if __name__ == '__main__':
    main()
