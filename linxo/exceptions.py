# -*- encoding: utf-8 -*-

"""
All exceptions are based from APIError
"""
import json


class APIError(Exception):
    """Base Linxo API exception, all specific exceptions inherits from it."""
    def __init__(self, *args, **kwargs):
        self.response = kwargs.pop('response', None)
        super(APIError, self).__init__(*args, **kwargs)

    def __str__(self):
        if self.response:
            return "{0} \nError: {1}".format(super(APIError, self).__str__(), json.dumps(self.response))
        else:
            return super(APIError, self).__str__()


class HTTPError(APIError):
    """Raised when the request fails at a low level (DNS, network, ...)"""


class InvalidEndpoint(APIError):
    """Raised when endpoint is not valid."""


class InvalidResponse(APIError):
    """Raised when api response is not valid json."""


class AuthentificationFailed(APIError):
    """Raise when api response is 401."""


class InvalidCredentials(APIError):
    """Raise when api response is 403."""


class ResourceNotFoundError(APIError):
    """Raised when requested resource does not exist."""


class NetworkError(APIError):
    """Raised when there is an error from network layer."""
