"""Module for local repositories."""

import os
import os.path
import logging
import repository

from repository import ConfigError, IoError, check_valid_required

from .file import RepositoryFile


class Repository(repository.Repository):
    """Repository with local file base."""

    # Required and valid configuration parameters
    CONF_REQ_KEYS = {'root'}
    CONF_VALID_KEYS = set() | CONF_REQ_KEYS

    def __init__(self, uuid, config, index=None):
        """Initialize repository with local file base.

        :param uuid: UUID of the repository.
        :type name: str
        :param root: Root directory of the repository.
        :type root: str
        :param index: Optional file metadata index. Default is None.
        :type index: repository.Index
        :raises: UuidError
        """
        # Call constructor of parent class
        repository.Repository.__init__(self, uuid, config, index)

        # Basic initialization.
        self._root = config['root']

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

    def _check_config(self, config):
        """Check the configuration for the repository from the configuration
        file.

        :param config:
        :type config: dict
        :raises: ConfigError
        """
        # Make sure valid and required parameters have been specified.
        check_valid_required(config, self.CONF_VALID_KEYS, self.CONF_REQ_KEYS)

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
        :raises: UuidError
        """
        return RepositoryFile(uuid, self, self._index, index_lookup, extract_metadata)

    @property
    def root(self):
        """Return root directory of the repository.

        :return: Root directory of repository.
        :rtype: str
        """
        return self._root


class FileIterator(repository.FileIterator):
    """Iterator which can be used to traverse through files in a repository with local file base."""

    def __init__(self, rep, index_lookup=True, extract_metadata=True):
        """Initialize file iterator.

        :param root: Repository with local file base.
        :type root: repository.local.repository
        :param index_lookup: True if file metadata shall be looked up from index.
        :type index_lookup: bool
        :param extract_metadata: True if file metadata shall be extracted from
            file if not available from index.
        :type extract_metadata: bool
        :raise: repository.IOError
        """
        self._rep = rep
        self._index_lookup = index_lookup
        self._extract_metadata = extract_metadata
        self._dir_list = []
        # Create scandir iterator for provided root directory
        try:
            self._iterator = os.scandir(self._rep.root)
        except Exception as e:
            raise IOError("An exception occurred while scanning directory:", e)

    def __next__(self):
        """Provide the next file.

        :returns: Next file in the repository.
        :rtype: repository.local.RepositoryFile
        :raises: StopIteration
        """
        try:
            # Retrieve the next directory entry.
            entry = self._iterator.__next__()
            # Continue to retrieve entries if not a file.
            while not entry.is_file():
                # Save all sub-directories for later.
                if entry.is_dir():
                    self._dir_list.append(entry.path)
                entry = self._iterator.__next__()

            # Construct relative path to root directory of the repository.
            uuid = os.path.relpath(entry.path, start=self._rep.root)
            # Return the next file.
            logging.debug(f"Creating next local repository file {uuid}.")
            return self._rep.file_by_uuid(uuid, self._index_lookup, self._extract_metadata)

        except StopIteration:
            if len(self._dir_list) > 0:
                # Start all over with first subdirectory in the list
                try:
                    self._iterator = os.scandir(self._dir_list.pop())
                except Exception as e:
                    raise IOError("An exception occurred while scanning directory:", e)
                return self.__next__()
            else:
                # Raise exception to indicate end of iteration otherwise
                raise StopIteration
