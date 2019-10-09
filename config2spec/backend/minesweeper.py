#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import os
import re
import sys
import requests

from config2spec.backend.response import Response
from config2spec.utils.logger import get_logger


class MinesweeperBackend(object):
    def __init__(self, base_path, scenario_name, config_path, url="http://localhost", port=8192, debug=False):
        self.logger = get_logger("MinesweeperBackend", "DEBUG" if debug else "INFO")

        self.base_path = base_path

        self.scenario_name = scenario_name
        self.config_path = config_path

        self.base_url = '%s:%d' % (url, port)

        self.init = False

    def post_request(self, attribute, data):
        try:
            response = requests.post(
                url='{base_url}/{attribute}'.format(base_url=self.base_url, attribute=attribute),
                data=data)
            response_content = response.content.decode('utf-8')
        except requests.exceptions.RequestException as e:
            # ConnectionError, Timeout, TooManyRedirects
            self.logger.error("Failed to connect to the Minesweeper Backend: {error}".format(error=e))
            sys.exit(1)

        self.logger.debug("\n\tResponse Code: %s\n\tContent: %s" % (response, response_content))

        return response, response_content

    def init_minesweeper(self, force_init=False):
        if not self.init or force_init:
            self.init = True

            # create a list of all config files in the config directory
            configs = list()
            all_files = os.listdir(self.config_path)
            for file_name in all_files:
                if '.' in file_name:
                    router, filetype = file_name.split('.')
                    if filetype == 'cfg' or filetype == 'conf':
                        configs.append(file_name)

            # submit commands to minesweeper service
            encoded_query = "BasePath:{base_path};ConfigPath:{config_path};ConfigFiles:{config_files}".format(
                base_path=self.base_path, config_path=self.config_path, config_files=','.join(configs))
            self.logger.info("Batfish Init Commands:\n{query}".format(query=encoded_query, ))
            response, response_content = self.post_request("init_minesweeper", encoded_query)

            # check that minesweeper initialization succeeded
            status = response_content
            output = True if "Success" in status else False
            return output
        else:
            self.logger.debug("MinesweeperBackend has already been initialized, no need to do it again.")
            return True

    def check_query(self, query):
        assert self.init, "The backend has to be initialized before querying it."

        self.logger.debug("Batfish Commands:\n{query}".format(query=query))

        encoded_query = query.to_string_representation()
        response, response_content = self.post_request("run_query", encoded_query)
        return Response(query, response_content.strip())

    def get_dataplane(self, failed_links=None):
        assert self.init, "The backend has to be initialized before querying it."

        encoded_query = ""
        if failed_links:
            encoded_query = "EdgeBlacklist:{edges}".format(edges=",".join(link.name for link in failed_links))
        response, response_content = self.post_request("get_dataplane", encoded_query)

        fib_file_match = re.match("^FIB:(fib-\d+.txt)$", response_content)

        if fib_file_match is None:
            return None
        else:
            return fib_file_match.group(1)

    def get_topology(self):
        assert self.init, "The backend has to be initialized before querying it."

        encoded_query = ""
        response, response_content = self.post_request("get_topology", encoded_query)

        files_regex = "^TOPO:(?P<topology>.*);INTERFACES:(?P<interfaces>.*);ACL:(?P<acls>.*)$"
        files_match = re.match(files_regex, response_content)

        if files_match is None:
            return None
        else:
            return files_match.groupdict()
