"""..."""


import logging

from abc import ABC, abstractmethod


class InvalidUuidError(Exception):
    """Invalid universal unique identifier (UUID) error."""

    def __init__(self, msg, uuid=None):
        super().__init__(msg)
        self.uuid = uuid


class Repository(ABC):
    """Repository of files.

    Abstract base class providing basic functionality common to all Repository
    sub-classes.
    """

    # Maximum length of uuid
    MAX_LEN_UUID = 36
    # Dictionary of all repositories by uuid
    _repositories = dict()

    def __init__(self, uuid, index=None):
        """Initialize the repository.

        :param uuid: UUID of the repository.
        :type uuid: str
        :param index: Optional file meta data index. Default is None.
        :type index: repository.Index
        :raises: InvalidUuidError
        """
        # Test uuid for validity
        if len(uuid) >= Repository.MAX_LEN_UUID:
            raise InvalidUuidError(f"UUID for repository too long. Maximum of {Repository.MAX_LEN_UUID} characters allowed.", uuid)
        # Warn if uuid already in use, but do not throw execption
        if uuid in Repository._repositories:
            logging.warn(f"UUID for repository '{uuid}' is already in use.")

        # Add self to dictionary of repositories
        Repository._repositories[uuid] = self
        # Initialize properties
        self._uuid = uuid
        self._index = index

    def __del__(self):
        """Delete the repository."""
        if self.uuid in Repository._repositories:
            del Repository._repositories[self.uuid]

    @abstractmethod
    def __iter__(self):
        """Provide iterator which allows to traverse through all files in the repository.

        :return: File iterator.
        :return type: repository.FileIterator
        """
        pass

    @staticmethod
    def by_uuid(uuid):
        """Return an existing repository instance by its UUID. Raises an
        InvalidUuidError if no repository with the specified UUID exists.

        :param uuid: UUID of the repository.
        :type uuid: str
        :return: Repository with matching UUID.
        :rtype: repository.Repository
        :raises: InvalidUuidError
        """
        if uuid in Repository._repositories:
            return Repository._repositories[uuid]
        else:
            raise InvalidUuidError(f"There is no repository with UUID '{uuid}'", uuid)

    @abstractmethod
    def file_by_uuid(self, uuid):
        """Return a file within the repository by its UUID. Raises an
        InvalidUuidError if the repository does not contain a file with the
        specified UUID.

        :param uuid: UUID of the file.
        :type uuid: str
        :return: File with matching UUID.
        :rtype: repository.RepositoryFile
        :raises: InvalidUuidError
        """
        pass

    @property
    def index(self):
        """Return meta data index of the repository.

        :return: Meta data index of the repository. May return None if no index
            was specified.
        :rtype: repository.Index
        """
        return self._index

    @index.setter
    def index(self, index):
        """Set meta data index of the repository.

        :param index: Meta data index of the repository.
        :type index: repository.Index
        """
        self._index = index

    @property
    def uuid(self):
        """Return UUID of the repository.

        : return: UUID of repository.
        : rtype: str
        """
        return self._uuid


class FileIterator:
    """Iterator which can be used to traverse through files in a repository."""

    @abstractmethod
    def __next__(self):
        """Provide the next file.

        : returns: Next file in the repository.
        : rtype: repository.RepositoryFile
        : raises: StopIteration
        """
        pass
