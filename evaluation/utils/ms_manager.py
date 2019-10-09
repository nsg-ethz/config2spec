#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import time
import os
import subprocess
import signal
import socket

from evaluation.utils.logger import get_logger


class MinesweeperManager(object):
    def __init__(self, command, port):
        self.process = None
        self.command = command
        self.running = False
        self.logger = get_logger('MinesweeperManager', 'INFO')
        self.queries = 0
        self.port = port

        self.backend = None

    def start(self):
        if not self.running:
            self.logger.info("Starting Minesweeper.")

            # make sure the port is available before starting Minesweeper
            while MinesweeperManager.port_blocked(self.port):
                self.logger.info("Port %d still blocked." % (self.port, ))
                time.sleep(0.5)

            # start Minesweeper
            self.logger.info("Port %d finally free, everything ready to start Minesweeper." % (self.port, ))
            self.process = subprocess.Popen(self.command, preexec_fn=os.setsid)
            self.running = True

            # wait a bit for Minesweeper to fully start up
            time.sleep(2.0)
        else:
            self.logger.info("Minesweeper is already running.")

    def stop(self, backend_calls, force_stop=False):
        self.queries += backend_calls
        if self.queries > 3500 or force_stop:
            self.logger.info("Killing Minesweeper as it answered %d queries - (force stop %s)" % (self.queries, force_stop))
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            self.running = False
            self.queries = 0
            return True
        else:
            self.logger.info("Keeping Minesweeper running as it answered just %d queries so far." % (self.queries, ))
            return False

    @staticmethod
    def port_blocked(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            sock.bind(("0.0.0.0", port))
            result = False
        except:
            result = True

        sock.close()
        return result

    def restart(self, backend_calls=0, force=False):
        assert self.backend, "Cannot restart the backend without self.ms_backend being set."

        # restart the backend/process
        stopped = self.stop(backend_calls=backend_calls, force_stop=force)
        if stopped:
            self.start()

            # init the restarted backend
            self.backend.init_minesweeper(force_init=True)

            # request topology such that the backend has already parsed the config
            self.backend.get_topology()

    def get_dataplane(self, failed_edges):
        return self.backend.get_dataplane(failed_edges)

    def check_query(self, query):
        # check if we should restart the backend
        self.queries += 1

        if self.queries > 3000:
            self.restart(force=True)

        return self.backend.check_query(query)
