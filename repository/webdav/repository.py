"""Module for WebDAV repositories."""


import logging
import repository
import tempfile

from repository.webdav import RepositoryFile
from repository import InvalidConfigurationError
from webdav3.client import Client


class Repository(repository.Repository):
    """Repository with WebDav file base."""

    def __init__(self, uuid, config, index=None):
        """Initialize repository with WebDav file base.

        :param uuid: UUID of the repository.
        :type name: str
        :param index: Optional file metadata index. Default is None.
        :type index: repository.Index
        :param config: Dictionary with repository Configuration
        :type config: dict
        :raises: InvalidUuidError
        """
        # Call constructor of parent class.
        repository.Repository.__init__(self, uuid, config, index)

        # Basic initialization.
        self._url = config['url']
        self._root = config['root']
        self._user = config['user']
        self._password = config['password']

        # Create temporary directory for file caching.
        self._cache_dir = tempfile.TemporaryDirectory(dir=config['cache'], prefix=f"{uuid}-")

        # Open WebDav client session.
        options = {
         'webdav_hostname': self._url,
         'webdav_login':    self._user,
         'webdav_password': self._password
        }
        self._client = Client(options)

    def _check_config(self, config):
        """Check the configuration for the repository from the configuration file.

        :param config:
        :type config: dict
        :raises: InvalidConfigurationError
        """
        # Extract defined parameters (keys).
        keys = set(config.keys())
        # Define allowed and required parameters (keys).
        required_keys = {"url", "user", "password"}
        allowed_keys = {"type", "url", "root", "user", "password", "enabled"}

        # Raise exception if minimum required parameters have not been defined.
        if not required_keys.issubset(keys):
            raise InvalidConfigurationError(f"Configuration for repository '{self.uuid}' is incomplete.", config)
        else:
            # Warn if additional, unused parameters have been defined.
            if not keys.issubset(allowed_keys):
                logging.warn(f"Configuration for repository '{self.uuid}' contains additional, unused parameters.")

    @property
    def cache_dir(self):
        """Return path to cache directory for temporary storage of files.

        :return: Path to cache directory.
        :rtype: str
        """
        return self._cache_dir.name

    @property
    def client(self):
        """Return WebDav client session of the repository.

        :return: WebDav client session.
        :rtype: webdav3.client.Client
        """
        return self._client

    @property
    def root(self):
        """Return WebDav root directory of the repository.

        :return: WebDav root directory.
        :rtype: str
        """
        return self._root

    def iterator(self, index_lookup=True, extract_metadata=True):
        """Provide iterator which allows to traverse through all files in the repository.

        :param index_lookup: True if file metadata shall be looked up from index.
        :type index_lookup: bool
        :param extract_metadata: True if file metadata shall be extracted from
            file if not available from index.
        :return: File iterator.
        :return type: repository.FileIterator
        """
        return FileIterator(self, index_lookup, extract_metadata)

    def file_by_uuid(self, uuid, index_lookup=True, extract_metadata=True):
        """Return a file within the repository by its UUID.

        :param uuid: UUID of the file.
        :type uuid: str
        :param index_lookup: True if file metadata shall be looked up from index.
        :type index_lookup: bool
        :param extract_metadata: True if file metadata shall be extracted from
            file if not available from index.
        :type extract_metadata: bool
        :return: File with matching UUID.
        :rtype: repository.RepositoryFile
        :raises: InvalidUuirError
        """
        return RepositoryFile(uuid, self, self._index, index_lookup, extract_metadata)


class FileIterator(repository.FileIterator):
    """Iterator which can be used to traverse through files in a webdav repository."""

    def __init__(self, rep, index_lookup=True, extract_metadata=True):
        """Initialize file iterator.

        :param root: Webdav repository.
        :type root: repository.webdav.repository
        :param index_lookup: True if file metadata shall be looked up from index.
        :type index_lookup: bool
        :param extract_metadata: True if file metadata shall be extracted from
            file if not available from index.
        :type extract_metadata: bool
        """
        # Basic initialization.
        self._rep = rep
        self._index_lookup = index_lookup
        self._extract_metadata = extract_metadata
        self._dir_list = []

        # Create iterator for list of root directory.
        self._file_list = rep.client.list(rep.root, get_info=True)
        self._iterator = iter(self._file_list)

    def __next__(self):
        """Provide the next file.

        :returns: Next file in the repository.
        :rtype: repository.webdav.RepositoryFile
        :raises: StopIteration
        """
        try:
            # Retrieve the next directory entry.
            entry = self._iterator.__next__()
            logging.debug(f"Current webdav directory entry: {entry}")
            # Continue to retrieve entries if not a file.
            while entry['isdir']:
                # Save all sub-directories for later.
                self._dir_list.append(entry['path'])
                entry = self._iterator.__next__()
                logging.debug(f"Current webdav directory entry: {entry}")

            # Construct relative path to root directory of the repository.
            uuid = entry['path']
            # Return the next file.
            logging.debug(f"Creating next webdav repository file {uuid}.")
            return self._rep.file_by_uuid(uuid, self._index_lookup, self._extract_metadata)

        except StopIteration:
            if len(self._dir_list) > 0:
                # Start all over with last subdirectory in the list
                self._file_list = self._rep.client.list(self._dir_list.pop(), get_info=True)
                self._iterator = iter(self._file_list)
                return self.__next__()
            else:
                # Raise exception to indicate end of iteration otherwise
                raise StopIteration
