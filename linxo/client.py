# -*- encoding: utf-8 -*-
import logging
import keyword
import json
import os

from builtins import input
from requests_oauthlib import OAuth2Session
from requests.exceptions import RequestException

from .exceptions import (
    APIError, InvalidEndpoint, HTTPError, InvalidResponse,
    AuthentificationFailed, InvalidCredentials, ResourceNotFoundError,
    NetworkError,
)

try:
    from urllib import urlencode
except ImportError:  # noqa
    from urllib.parse import urlencode

from .config import config

#: Mapping between Linxo API environnement
ENDPOINTS = {
    'prod': {
        'api_url': 'https://api.linxo.com/v2',
        'auth_url': 'https://auth.linxo.com',
    },
    'preprod': {
        'api_url': 'https://api-pprd.api.linxo.com/v2',
        'auth_url': 'https://auth-pprd.api.linxo.com',
    },
    'sandbox': {
        'api_url': 'https://sandbox-api.linxo.com/v2',
        'auth_url': 'https://sandbox-auth.linxo.com',
    },
}

#: Default timeout for each request. 180 seconds connect, 180 seconds read.
TIMEOUT = 180

#: Redirect URI for token generation
REDIRECT_URI = os.environ.get('LINXO_REDIRECT_URI',
                              'http://localhost:8012/callback')

def get_code(text):
    """Wrapper for input so as to mock."""
    return input(text)


class Client(object):
    def __init__(self, endpoint=None, client_id=None, client_secret=None,
                 access_token=None, refresh_token=None, config_file=None,
                 timeout=TIMEOUT, debug=False):
        """Creates a new Client. No credential check is done at this point."""
        if config_file:
            config.read(config_file)

        if endpoint is None:
            endpoint = config.get('default', 'endpoint')
        self.endpoint = endpoint

        try:
            self._endpoint = ENDPOINTS[endpoint]
        except KeyError:
            raise InvalidEndpoint("Unknow endpoint %s. Valid endpoints: %s",
                                  endpoint, ENDPOINTS.keys())

        if client_id is None:
            client_id = config.get(endpoint, 'client_id')
        self._client_id = client_id

        if client_secret is None:
            client_secret = config.get(endpoint, 'client_secret')
        self._client_secret = client_secret

        if access_token is None:
            access_token = config.get(endpoint, 'access_token')
        self._access_token = access_token

        if refresh_token is None:
            refresh_token = config.get(endpoint, 'refresh_token')
        self._refresh_token = refresh_token

        # Override default timeout
        self._timeout = timeout

        self.token_url = self._endpoint['auth_url'] + '/tokens'

        self._session = OAuth2Session(client_id=client_id,
                                      token={'access_token': access_token,
                                             'refresh_token': refresh_token})

        self.debug = debug

    def _debug(self, data):
        if self.debug:
            logging.debug(data)

    def _canonicalize_kwargs(self, kwargs):
        """
        If an API needs an argument colliding with a Python reserved keyword, it
        can be prefixed with an underscore.
        """
        arguments = {}

        for k, v in kwargs.items():
            if k[0] == '_' and k[1:] in keyword.kwlist:
                k = k[1:]
            arguments[k] = v

        return arguments

    def _prepare_query_string(self, kwargs):
        """
        Boolean needs to be send as lowercase 'false' or 'true' in querystring.
        This function prepares arguments for querystring and encodes them.
        """
        arguments = {}

        for k, v in kwargs.items():
            if isinstance(v, bool):
                v = str(v).lower()
            arguments[k] = v

        return urlencode(arguments)

    def generate_token(self, scopes=[]):
        """Generate a URL and wait for a code to update token."""
        authorization_url, state = self.generate_auth_url(scopes)

        # Print information
        print('Please navigate to {0} and login'.format(authorization_url))
        print('Once this is done, you will be redirected to {0}'.format(REDIRECT_URI))
        code = get_code('Please enter the part after code: ')

        linxo = OAuth2Session(client_id=self._client_id, state=state, redirect_uri=REDIRECT_URI)
        token = linxo.fetch_token(self.token_url, client_secret=self._client_secret, code=code)
        for key in ['access_token', 'refresh_token']:
            if key not in token:
                raise Exception('{0} not in token answer'.format(key))
            else:
                print('{0} is {1}'.format(key, token[key]))
        self._save_token(token)

    def generate_auth_url(self, scopes=[]):
        """Generate a URL and an oauth state."""
        valid_scopes = [
            'accounts_manage',
            'accounts_read',
            'connections_manage',
            'connections_sync',
            'transactions_read',
            'users_create']
        real_scopes = ['openid']
        for scope in scopes:
            if scope not in valid_scopes:
                logging.warning('Skipping invalid scope {0}'.format(scope))
            else:
                real_scopes.append(scope)

        auth_url = self._endpoint['auth_url'] + '/signin'
        linxo = OAuth2Session(client_id=self._client_id, redirect_uri=REDIRECT_URI)
        authorization_url, state = linxo.authorization_url(auth_url)

        correct_scope = '%20'.join(real_scopes)
        final_url = '{0}&scope={1}'.format(authorization_url, correct_scope)

        return final_url, state

    def get(self, _target, **kwargs):
        """
        'GET' :py:func:`Client.call` wrapper.
        Query string parameters can be set either directly in ``_target`` or as
        keywork arguments. If an argument collides with a Python reserved
        keyword, prefix it with a '_'. For instance, ``from`` becomes ``_from``.
        """
        if kwargs:
            kwargs = self._canonicalize_kwargs(kwargs)
            query_string = self._prepare_query_string(kwargs)
            if '?' in _target:
                _target = '%s&%s' % (_target, query_string)
            else:
                _target = '%s?%s' % (_target, query_string)

        return self.call('GET', _target, None)

    def put(self, _target, **kwargs):
        """
        'PUT' :py:func:`Client.call` wrapper
        Body parameters can be set either directly in ``_target`` or as keywork
        arguments. If an argument collides with a Python reserved keyword,
        prefix it with a '_'. For instance, ``from`` becomes ``_from``.
        """
        kwargs = self._canonicalize_kwargs(kwargs)
        return self.call('PUT', _target, kwargs)

    def post(self, _target, **kwargs):
        """
        'POST' :py:func:`Client.call` wrapper
        Body parameters can be set either directly in ``_target`` or as keywork
        arguments. If an argument collides with a Python reserved keyword,
        prefix it with a '_'. For instance, ``from`` becomes ``_from``.
        """
        kwargs = self._canonicalize_kwargs(kwargs)
        return self.call('POST', _target, kwargs)

    def delete(self, _target):
        """
        'DELETE' :py:func:`Client.call` wrapper
        """
        return self.call('DELETE', _target, None)

    def call(self, method, path, data=None):
        """Low level call helper."""
        # request
        try:
            result = self.raw_call(method=method, path=path, data=data)
        except RequestException as error:
            raise HTTPError("Low HTTP request failed error", error)

        status = result.status_code

        # decode json
        try:
            json_result = result.json()
        except ValueError as error:
            raise InvalidResponse("Failed to decode API response", error)

        # error check
        if status >= 100 and status < 300:
            return json_result
        elif status == 401:
            raise AuthentificationFailed(json_result.get('error_description'),
                                         response=result)
        elif status == 403:
            raise InvalidCredentials(json_result.get('error_description'),
                                     response=result)
        elif status == 404:
            raise ResourceNotFoundError(json_result.get('error_description'),
                                        response=result)
        elif status == 0:
            raise NetworkError()
        else:
            raise APIError(json_result.get('error_description'), response=result)

    def _renew_token(self):
        """Renew a token, and save it."""
        token = self._session.refresh_token(self.token_url,
                                            client_id=self._client_id,
                                            client_secret=self._client_secret)
        self._session.token = token
        self._save_token(token)

    def _save_token(self, token):
        """Once a new token has been generate, save it to config file."""
        config.set(self.endpoint, 'access_token', token.get('access_token'))
        config.set(self.endpoint, 'refresh_token', token.get('refresh_token'))
        config.write()

    def raw_call(self, method, path, data=None):
        """Lowest level call helper."""

        body = ''
        target = self._endpoint['api_url'] + path
        headers = {}

        # include payload
        if data is not None:
            headers['Content-type'] = 'application/json'
            body = json.dumps(data)

        r = self._session.request(method, target, headers=headers,
                                  data=body, timeout=self._timeout)

        if r.status_code == 401:
            logging.info('Got a 401, renewing token')
            self._renew_token()

            return self._session.request(method, target, headers=headers,
                                        data=body, timeout=self._timeout)
        else:
            return r
