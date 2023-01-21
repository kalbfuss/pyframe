"""Module for local repositories."""


import os
import os.path
import logging
import repository

from repository import InvalidConfigurationError
from repository.local import RepositoryFile


class Repository(repository.Repository):
    """Repository with local file base."""

    def __init__(self, uuid, config, index=None):
        """Initialize repository with local file base.

        :param uuid: UUID of the repository.
        :type name: str
        :param root: Root directory of the repository.
        :type root: str
        :param index: Optional file meta data index. Default is None.
        :type index: repository.Index
        :raises: InvalidUuidError
        """
        # Call constructor of parent class
        repository.Repository.__init__(self, uuid, config, index)

        # Basic initialization.
        self._root = config['root']

    def iterator(self, index_lookup=True):
        """Provide iterator which allows to traverse through all files in the repository.

        :param index_lookup: True if file metadata shall be looked up from index.
        :type index_lookup: bool
        :return: File iterator.
        :return type: repository.FileIterator
        """
        return FileIterator(self, index_lookup)

    def _check_config(self, config):
        """Check the configuration for the repository from the configuration file.

        :param config:
        :type config: dict
        :raises: InvalidConfigurationError
        """
        # Extract defined parameters (keys).
        keys = set(config.keys())
        # Define allowed and required parameters (keys).
        required_keys = {"root"}
        allowed_keys = {"type", "root", "enabled"}

        # Raise exception if minimum required parameters have not been defined.
        if not required_keys.issubset(keys):
            raise InvalidConfigurationError(f"Configuration for repository '{self.uuid}' is incomplete.", config)
        else:
            # Warn if additional, unused parameters have been defined.
            if not keys.issubset(allowed_keys):
                logging.warn(f"Configuration for repository '{self.uuid}' contains additional, unused parameters.")

    def file_by_uuid(self, uuid, index_lookup=True):
        """Return a file within the repository by its UUID.

        :param uuid: UUID of the file.
        :type uuid: str
        :param index_lookup: True if file metadata shall be looked up from index.
        :type index_lookup: bool
        :return: File with matching UUID.
        :rtype: repository.RepositoryFile
        :raises: InvalidUuidError
        """
        if index_lookup:
            return RepositoryFile(uuid, self, self._index)
        else:
            return RepositoryFile(uuid, self)

    @property
    def root(self):
        """Return root directory of the repository.

        :return: Root directory of repository.
        :rtype: str
        """
        return self._root


class FileIterator(repository.FileIterator):
    """Iterator which can be used to traverse through files in a repository with local file base."""

    def __init__(self, rep, index_lookup=True):
        """Initialize file iterator.

        :param root: Repository with local file base.
        :type root: repository.local.repository
        :param index_lookup: True if file metadata shall be looked up from index.
        :type index_lookup: bool
        """
        self._rep = rep
        self._index_lookup = index_lookup
        self._dir_list = []
        # Create scandir iterator for provided root directory
        self._iterator = os.scandir(self._rep.root)

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
            return self._rep.file_by_uuid(uuid, self._index_lookup)

        except StopIteration:
            if len(self._dir_list) > 0:
                # Start all over with first subdirectory in the list
                self._iterator = os.scandir(self._dir_list.pop())
                return self.__next__()
            else:
                # Raise exception to indicate end of iteration otherwise
                raise StopIteration