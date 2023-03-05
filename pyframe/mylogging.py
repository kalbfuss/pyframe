"""Module providing pyframe log handler."""

import os
import threading

from logging import Handler, Formatter
from logging.handlers import TimedRotatingFileHandler


# Global oyframe log handler. Initialized by application build function.
logHandler = None

class LogHandler(Handler):
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

        # Create one rotating file handler per specified thread.
        formatter = Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
        for name in thread_names:
            self._handlers[name] = TimedRotatingFileHandler(os.path.join(dir_name, f"{name}.log"), when="h", interval=24, backupCount=5)
            self._handlers[name].setFormatter(formatter)
        # Create rotating file handler for main thread
        name = threading.main_thread().name
        self._handlers[name] = TimedRotatingFileHandler(os.path.join(dir_name, f"pyframe.log"), when="h", interval=24, backupCount=5)
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
