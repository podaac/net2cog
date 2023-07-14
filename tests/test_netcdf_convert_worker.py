# """
# ===================
# test_netcdf_convert_worker.py
# ===================
#
# Test the netcdf_convert_worker functionality
# """

import os
import unittest
from unittest.mock import patch
import pytest
import logging

from podaac.netcdf_converter.netcdf_convert_worker import NCWorker

os.environ['PODAAC_MESSAGEBUS_TOPIC_ARN'] = 'podaac-message-bus-arn'


class NCWorkerTests(unittest.TestCase):
    """
    Test netcdf_convert_worker.py
    """

    @patch('podaac.netcdf_converter.netcdf_convert.netcdf_converter')
    def test_file_paths(self, mock_nc):
        """
        Test that the process function parses the bbox coordinates correctly
        """
        # self._caplog.set_level(logging.INFO)

        test_message = {
            'identifier': 'unit',
            'stagedOutputLocations': ['s3://test'],
            'resources': [
                {
                    'type': 'resource',
                    'href': 'http://dummy.url.com'
                },
                {
                    'href': 's3://dummy.url.com',
                    'type': 'resource'
                }
            ],
            'meta': {
                'processedFiles': ["/where/are.you"]
            }
        }

        nc_worker = NCWorker("test-queue")

        with patch('os.makedirs'):
            nc_worker.process(test_message)

        mock_nc.assert_called_once()
        print(mock_nc.call_args)

