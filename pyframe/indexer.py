"""Module providing file indexer."""

import logging
import os
import threading

from logging import Handler, Formatter
from logging.handlers import TimedRotatingFileHandler
from repository import Index
from threading import Thread
from time import time, sleep

from kivy.logger import Logger


# Create a special logger that logs to per-thread-name files
# I'm not confident the locking strategy here is correct, I think this is
# a global lock and it'd be OK to just have a per-thread or per-file lock.
class IndexerLogHandler(Handler):

    def __init__(self, dir_name, thread_names):
        super().__init__()
        self._handlers = dict()

        # Create log directory if it does not exist yet.
        os.makedirs(dir_name, exist_ok=True)
        # Make sure the directory is writable.
        if not os.access(dir_name, os.W_OK):
            raise Exception(f"Directory {dir_name} is not writeable. Log files cannot be created.")

        # Convert thread_names to list if only single thread name specified.
        if type(thread_names) == str:
            thread_names = [thread_names]

        # Create one rotating file handler per thread
        formatter = Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
        for name in thread_names:
            self._handlers[name] = TimedRotatingFileHandler(os.path.join(dir_name, f"{name}.log"), when="h", interval=24, backupCount=5)
            self._handlers[name].setFormatter(formatter)

    def emit(self, record):
        name = threading.current_thread().name
        if name in self._handlers:
            try:
                self._handlers[name].emit(record)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.handleError(record)

    def flush(self):
        name = threading.current_thread().name
        if name in self._handlers:
            self._handlers[name].handler.flush()

    def setFormatter(self, formatter):
        self.acquire()
        for name, handler in self._handlers.items():
            handler.setFormatter(formatter)
        self.release()

    def setPrefix(self, *args):
        if len(args) == 0 or args[0] == "":
            fmt_str = f"%(asctime)s %(message)s"
        else:
            fmt_str = f"%(asctime)s [{args[0]}] %(message)s"
        formatter = Formatter(fmt_str, "%Y-%m-%d %H:%M:%S")
        self.setFormatter(formatter)


class RepData:
    def __init__(self, interval=0):
        self.interval = interval
        self.next = time()
        self.last = 0


class Indexer:

    def __init__(self, index):
        self._rep_data = dict()
        self._thread = None
        self._index = index

        # Configure indexer logger.
        self._handler = IndexerLogHandler("./log", "indexer")
        logging.getLogger().addHandler(self._handler)
        # Reduce logging by IPTCInfo and exifread to errors.
        logging.getLogger("iptcinfo").setLevel(logging.ERROR)
        logging.getLogger("exifread").setLevel(logging.ERROR)


    def _build(self):

        def format_duration(duration):
            if duration > 3600:
                duration_str = f"{duration/3600:.1f} hours"
            if duration > 60:
                duration_str = f"{duration/60:.1f} minutes"
            else:
                duration_str = f"{duration:.1f} seconds"
            return duration_str

        pause_until = time()

        logging.info(f"Starting to build meta data index in the background.")
        while True:
            for rep in list(self._rep_data.keys()):
                cur_time = time()
                data = self._rep_data[rep]
                if data.last == 0 or (data.interval > 0 and data.next < cur_time):
                    self._handler.setPrefix(rep.uuid)
                    self._index.build(rep)
                    end_time = time()
                    duration = (end_time - cur_time)
                    logging.info(f"Indexing of repository '{rep.uuid}' completed after {format_duration(duration)}.")
                    data.last = end_time
                    data.next = end_time + data.interval*3600
                elif data.last > 0 and data.interval == 0:
                    self._rep_data.pop(rep)
                    logging.info(f"Removing repository '{rep.uuid}' from queue.")
                elif data.next > pause_until and data.interval > 0:
                    pause_until = data.next

            self._handler.setPrefix()

            if len(self._rep_data) == 0:
                logging.info(f"Stopping to build meta data index in the background.")
                return

            cur_time = time()
            if pause_until > cur_time:
                duration = (pause_until - cur_time)
                logging.info(f"Sleeping for {format_duration(duration)}.")
                sleep(duration)

    def queue(self, rep, interval=0):
        Logger.info(f"Indexer: Queuing repository '{rep.uuid}' for indexing of meta data.")
        self._rep_data[rep] = RepData(interval=interval)

    def start(self):
        Logger.info(f"Indexer: Starting to build meata data index in the background.")
        self._thread = Thread(name="indexer", target=self._build, daemon=True)
        self._thread.start()
