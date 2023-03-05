"""Module providing meta data background indexer."""

import logging
import os
import threading

from logging import Handler, Formatter
from logging.handlers import TimedRotatingFileHandler
from repository import Index, IOError
from threading import Thread
from time import asctime, localtime, mktime, time, sleep

from kivy.logger import Logger


class IndexerLogHandler(Handler):
    """Log handler for meta data background indexer.

    Redirects log messages from selected (background) threads to rotating log
    files. Used to separate messages generated during indexing in the background
    from foreground log messages.
    Threads are identified by their names. The handler creates one log file per
    thread. The name of the log file is identical to the name of the thread plus
    the suffix ".log".
    Log files are rotated once per day and a maximum of 5+1 log files is kept.
    """

    def __init__(self, dir_name, thread_names):
        """Initialize IndexLogHandler instance.

        :param dir_name: Directory for the log files (path). The path must be
          writable. The directory is created if it does not exist.
        :type dir_name: str
        :param thread_name: Name of the threads for wich log messages shall be
          redirected to a rotating log file.
        :type thread_names: list of str or str (single thread)
        :raises: Raises an exception if the directory cannot be created or is
          not writable.
        """
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

        # Create one rotating file handler per thread.
        formatter = Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
        for name in thread_names:
            self._handlers[name] = TimedRotatingFileHandler(os.path.join(dir_name, f"{name}.log"), when="h", interval=24, backupCount=5)
            self._handlers[name].setFormatter(formatter)

    def emit(self, record):
        """Log the specified logging record."""
        name = threading.current_thread().name
        if name in self._handlers:
            try:
                self._handlers[name].emit(record)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.handleError(record)

    def flush(self):
        "Ensure all logging output has been flushed."
        name = threading.current_thread().name
        if name in self._handlers:
            self._handlers[name].handler.flush()

    def setFormatter(self, formatter):
        "Set the formatter for this handler."
        self.acquire()
        for name, handler in self._handlers.items():
            handler.setFormatter(formatter)
        self.release()

    def setPrefix(self, *args):
        """Set a message prefix.

        The prefix is cleared if the message is called without arguments or an
        empty string is provided.
        :param *args: Message prefix
        :type *args: str
        """
        # Clear prefix if no argument specified or empty string.
        if len(args) == 0 or args[0] == "":
            fmt_str = f"%(asctime)s %(message)s"
        # Set message prefix.
        else:
            fmt_str = f"%(asctime)s [{args[0]}] %(message)s"
        formatter = Formatter(fmt_str, "%Y-%m-%d %H:%M:%S")
        self.setFormatter(formatter)


class RepData:
    """Repository data structure.

    Used by the Idexer class to store information about queued repositories.
    """

    def __init__(self, interval=0, at=None):
        """Initialize RepData instance.

        : param interval: Index update interval in hours
        : type interval: int
        """
        self.interval = interval
        # Convert time string to numeric array.
        if at is not None:
            self.at = [int(s) for s in at.split(":")]
        else:
            self.at = None
        self.last = 0
        self.next = 0
        self.update_next()

    def update_next(self, last=None):
        """Returns ..."""
        # Update time of last run if specified.
        if last is not None:
            self.last = last
        # Determine time of next run.
        if self.at is not None:
            lt = localtime()
            offset = 0
            if self.at[0] < lt.tm_hour or (self.at[0] == lt.tm_hour and self.at[1] <= lt.tm_min):
                offset = 24*3600
            nt = (lt[0], lt[1], lt[2], self.at[0], self.at[1], 0, lt[6], lt[7], lt[8])
            self.next = offset + mktime(nt)
        elif self.last == 0:
            self.next = time()
        elif self.last > 0 and self.interval > 0:
            self.next = self.last + self.interval*3600
        else:
            self.next = 0


class Indexer:
    """Meta data background indexer.

    Used by the pyframe application to build the meta data index for active
    repositories in the background. The index is built using the
    repository.Index class.
    The index is built at least once for all queued repositories. If
    an update interval or time is specified, the index is built periodically
    for the respective repository.
    The class uses a special log handler IndexerLogHandler to redirect log
    messages from the background thread to a rotated log file.
    """

    def __init__(self, index):
        """Initialize Indexer instance.

        : param index: The index instance used to build the meta data index.
        : type index: repository.Index
        """
        self._rep_data = dict()
        self._thread = None
        self._index = index

        # Redirect all log messages from the background thread into a rotated
        # log file using a special log handler.
        self._handler = IndexerLogHandler("./log", "indexer")
        logging.getLogger().addHandler(self._handler)
        # Reduce logging by IPTCInfo and exifread to errors.
        logging.getLogger("iptcinfo").setLevel(logging.ERROR)
        logging.getLogger("exifread").setLevel(logging.ERROR)

    def _build(self):
        """Build meta data index for queued repositories.

        The method is executed in a background thread. The background thread
        is created and started by the start method. The _build method runs
        infinitely or until the queue of repositories is empty.
        """

        def format_duration(duration):
            """Helper function to format duration string.

            : param duration: Duration in seconds
            : type duration: int
            : return: Duration and unit as formatted string
            : rtype: str
            """
            if duration > 3600:
                duration_str = f"{duration/3600:.1f} hours"
            if duration > 60:
                duration_str = f"{duration/60:.1f} minutes"
            else:
                duration_str = f"{duration:.1f} seconds"
            return duration_str

        pause_until = 0
        logging.info(f"Starting to build meta data index in the background.")

        while True:
            # Iterate through repositories, which have been queued for indexing.
            for rep in list(self._rep_data.keys()):

                cur_time = time()
                data = self._rep_data[rep]

                # Build index for repository if due, but at least once.
                if data.next < cur_time:
                    # Set log prefix to uuid of current repository.
                    self._handler.setPrefix(rep.uuid)
                    # Build meta data index for current repository.
                    try:
                        self._index.build(rep)
                    except IOError as e:
                        logging.error(f"An I/O error occurred while indexing the repository: {e.exception}")
                    # Log duration of indexing run.
                    end_time = time()
                    duration = (end_time - cur_time)
                    logging.info(f"Indexing of repository '{rep.uuid}' completed after {format_duration(duration)}.")
                    # Record completion time and update time for next indexing
                    # run.
                    data.update_next(end_time)
                    if data.next > 0:
                        # Log time of next indexing run.
                        logging.info(f"The next indexing run is due at {asctime(localtime(data.next))}.")
                    else:
                        logging.info(f"Removing repository '{rep.uuid}' from queue.")
                        self._rep_data.pop(rep)

                    # Clear log prefix
                    self._handler.setPrefix()

                if pause_until == 0 or (data.next > 0 and data.next < pause_until):
                    pause_until = data.next

            # Stop building index if there are no more repositories queued.
            if len(self._rep_data) == 0:
                logging.info(f"Stopping to build meta data index in the background.")
                return

            # If necessary, sleep until next repository is due for indexing.
            cur_time = time()
            if pause_until > cur_time:
                # Log duration until next indexing run is due.
                duration = (pause_until - cur_time)
                pause_until = 0
                logging.info(f"Sleeping for {format_duration(duration)}.")
                sleep(duration)

    def queue(self, rep, interval=0, at=None):
        """Queue repositories for indexing.

        Repositories must be queued prior to starting index creation. It is not
        safe to queue repositories after index creation has been started.

        : param rep: Repository to be queued for indexing.
        : type rep: repository.RepositoryFile
        : param interval: Index update interval in hours. No value or a value of
          zero means that the index is created only once after start up.
        : type interval: int
        """
        Logger.info(f"Indexer: Queuing repository '{rep.uuid}' for indexing of meta data.")
        self._rep_data[rep] = RepData(interval, at)

    def start(self):
        """Start index creation in the background.

        Creates a background thread, which executes the _build method.
        Repositories must have been queued before. It is not safe to queue
        repositories after index creation has been started.
        """
        Logger.info(f"Indexer: Starting to build meata data index in the background.")
        self._thread = Thread(name="indexer", target=self._build, daemon=True)
        self._thread.start()
