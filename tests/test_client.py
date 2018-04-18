# -*- encoding: utf-8 -*-

import unittest
import mock
import json
import requests

from linxo.client import Client
from linxo.exceptions import (
    APIError, NetworkError, InvalidResponse, HTTPError, InvalidEndpoint,
    AuthentificationFailed, InvalidCredentials, ResourceNotFoundError,
)

M_CUSTOM_CONFIG_PATH = './tests//fixtures/custom_linxo.conf'

CLIENT_ID = 'fake client_id'
CLIENT_SECRET = 'fake client_secret'
REFRESH_TOKEN = 'fake refresh_token'
ENDPOINT = 'prod'
ENDPOINT_BAD = 'laponie'
API_URL = 'https://api.linxo.com/v2'
AUTH_URL = 'https://auth.linxo.com'
FAKE_URL = 'http://gopher.linxo.com/'
FAKE_TIME = 1404395889.467238

FAKE_METHOD = 'MeThOd'
FAKE_PATH = '/unit/test'

TIMEOUT = 180


class testClient(unittest.TestCase):
    def setUp(self):
        self.time_patch = mock.patch('time.time', return_value=FAKE_TIME)
        self.time_patch.start()

    def tearDown(self):
        self.time_patch.stop()

    # test helpers

    def test_init(self):
        # nominal
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
        self.assertEqual(CLIENT_ID, api._client_id)
        self.assertEqual(CLIENT_SECRET, api._client_secret)
        self.assertEqual(REFRESH_TOKEN, api._refresh_token)
        self.assertEqual(TIMEOUT, api._timeout)

        # override default timeout
        timeout = (1, 1)
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET,
                     REFRESH_TOKEN, timeout=timeout)
        self.assertEqual(timeout, api._timeout)

        # invalid region
        self.assertRaises(InvalidEndpoint, Client, ENDPOINT_BAD, '', '', '')

    def test_init_from_custom_config(self):
        # custom config file
        api = Client(config_file=M_CUSTOM_CONFIG_PATH)

        self.assertEqual('https://sandbox-api.linxo.com/v2', api._endpoint['api_url'])
        self.assertEqual('https://sandbox-auth.linxo.com', api._endpoint['auth_url'])
        self.assertEqual('custom client_id', api._client_id)
        self.assertEqual('custom client_secret', api._client_secret)
        self.assertEqual('custom refresh_token', api._refresh_token)

    @mock.patch('linxo.client.OAuth2Session.authorization_url')
    def test_generate_auth_url(self, m_req):
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)

        # nominal
        FAKE_SCOPES = ['users_create']
        FAKE_STATE = 'fake state'
        m_req.return_value = AUTH_URL, FAKE_STATE

        url, state = api.generate_auth_url(FAKE_SCOPES)

        self.assertEqual(url, AUTH_URL + '&scope=openid%20users_create')
        self.assertEqual(state, FAKE_STATE)
        m_req.assert_called_once_with(AUTH_URL + '/signin')

    @mock.patch('linxo.client.get_code', return_value='fake_code')
    @mock.patch('linxo.client.OAuth2Session.fetch_token')
    def test_generate_token(self, m_req, m_code):

        # Overwrite configuration to avoid interfering with any local config
        from linxo.client import config
        try:
            from ConfigParser import RawConfigParser
        except ImportError:
            # Python 3
            from configparser import RawConfigParser

        self._orig_config = config.config
        config.config = RawConfigParser()

        config.config.add_section('prod')
        config.config.set('prod', 'client_id', CLIENT_ID)
        config.config.set('prod', 'client_secret', CLIENT_SECRET)
        config.config.set('prod', 'refresh_token', REFRESH_TOKEN)
        config.filename = '/tmp/test'
        config.write()

        m_req.return_value = {
            'refresh_token': 'fake generated refresh_token',
            'access_token': 'fake generated access_token',
        }

        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)

        api.generate_token()

        m_req.assert_called_once_with(AUTH_URL + '/token',
                                      client_secret=CLIENT_SECRET,
                                      code='fake_code')

        config.read('/tmp/test')
        self.assertEqual(config.config.get('prod', 'refresh_token'), 'fake generated refresh_token')

        api.set_token(m_req.return_value)
        self.assertEqual(api._session.token['refresh_token'], 'fake generated refresh_token')

        config.config = self._orig_config

    def test__canonicalize_kwargs(self):
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)

        self.assertEqual({}, api._canonicalize_kwargs({}))
        self.assertEqual({'from': 'value'}, api._canonicalize_kwargs({'from': 'value'}))
        self.assertEqual({'_to': 'value'}, api._canonicalize_kwargs({'_to': 'value'}))
        self.assertEqual({'from': 'value'}, api._canonicalize_kwargs({'_from': 'value'}))

    @mock.patch.object(Client, 'call')
    def test_get(self, m_call):
        # basic test
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)
        self.assertEqual(m_call.return_value, api.get(FAKE_URL))
        m_call.assert_called_once_with('GET', FAKE_URL, None)

        # append query string
        m_call.reset_mock()
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)
        self.assertEqual(m_call.return_value, api.get(FAKE_URL, param="test"))
        m_call.assert_called_once_with('GET', FAKE_URL + '?param=test', None)

        # append to existing query string
        m_call.reset_mock()
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)
        self.assertEqual(m_call.return_value, api.get(FAKE_URL + '?query=string', param="test"))
        m_call.assert_called_once_with('GET', FAKE_URL + '?query=string&param=test', None)

        # boolean arguments
        m_call.reset_mock()
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)
        self.assertEqual(m_call.return_value, api.get(FAKE_URL + '?query=string', checkbox=True))
        m_call.assert_called_once_with('GET', FAKE_URL + '?query=string&checkbox=true', None)

        # keyword calling convention
        m_call.reset_mock()
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)
        self.assertEqual(m_call.return_value, api.get(FAKE_URL, _from="start", to="end"))
        try:
            m_call.assert_called_once_with('GET', FAKE_URL + '?to=end&from=start', None)
        except Exception:
            m_call.assert_called_once_with('GET', FAKE_URL + '?from=start&to=end', None)

    @mock.patch.object(Client, 'call')
    def test_delete(self, m_call):
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)
        self.assertEqual(m_call.return_value, api.delete(FAKE_URL))
        m_call.assert_called_once_with('DELETE', FAKE_URL, None)

    @mock.patch.object(Client, 'call')
    def test_post(self, m_call):
        PAYLOAD = {
            'arg1': object(),
            'arg2': object(),
            'arg3': object(),
            'arg4': False,
        }

        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)
        self.assertEqual(m_call.return_value, api.post(FAKE_URL, **PAYLOAD))
        m_call.assert_called_once_with('POST', FAKE_URL, PAYLOAD)

    @mock.patch.object(Client, 'call')
    def test_put(self, m_call):
        PAYLOAD = {
            'arg1': object(),
            'arg2': object(),
            'arg3': object(),
            'arg4': False,
        }

        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)
        self.assertEqual(m_call.return_value, api.put(FAKE_URL, **PAYLOAD))
        m_call.assert_called_once_with('PUT', FAKE_URL, PAYLOAD)

    # test core function

    @mock.patch('linxo.client.OAuth2Session.request')
    def test_call_no_sign(self, m_req):
        m_res = m_req.return_value
        m_json = m_res.json.return_value

        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)

        # nominal
        m_res.status_code = 200
        self.assertEqual(m_json, api.call(FAKE_METHOD, FAKE_PATH, None))
        m_req.assert_called_once_with(
            FAKE_METHOD, API_URL + '/unit/test',
            headers={},
            data='',
            timeout=TIMEOUT
        )
        m_req.reset_mock()

        # data, nominal
        m_res.status_code = 200
        data = {'key': 'value'}
        j_data = json.dumps(data)
        self.assertEqual(m_json, api.call(FAKE_METHOD, FAKE_PATH, data))
        m_req.assert_called_once_with(
            FAKE_METHOD, API_URL + '/unit/test',
            headers={
                'Content-type': 'application/json',
            }, data=j_data, timeout=TIMEOUT
        )
        m_req.reset_mock()

        # request fails, somehow
        m_req.side_effect = requests.RequestException
        self.assertRaises(HTTPError, api.call, FAKE_METHOD, FAKE_PATH, None)
        m_req.side_effect = None

        # response decoding fails
        m_res.json.side_effect = ValueError
        self.assertRaises(InvalidResponse, api.call, FAKE_METHOD, FAKE_PATH, None)
        m_res.json.side_effect = None

        # HTTP errors
        m_res.status_code = 404
        self.assertRaises(ResourceNotFoundError, api.call, FAKE_METHOD, FAKE_PATH, None)
        m_res.status_code = 401
        self.assertRaises(AuthentificationFailed, api.call, FAKE_METHOD, FAKE_PATH, None)
        m_res.status_code = 403
        m_res.json.return_value = {'error_description': "INVALID_CREDENTIALS"}
        self.assertRaises(InvalidCredentials, api.call, FAKE_METHOD, FAKE_PATH, None)
        m_res.status_code = 0
        self.assertRaises(NetworkError, api.call, FAKE_METHOD, FAKE_PATH, None)
        m_res.status_code = 99
        m_res.json.return_value = {'error_description': 'toto', 'response': 'toto'}
        self.assertRaises(APIError, api.call, FAKE_METHOD, FAKE_PATH, None)
        m_res.status_code = 306
        self.assertRaises(APIError, api.call, FAKE_METHOD, FAKE_PATH, None)

    raw_call_mock = mock.MagicMock()
    raw_call_mock.status_code = 200
    raw_call_mock.txt = "Let's assume requests will return this"

    @mock.patch('linxo.client.OAuth2Session.request', return_value=raw_call_mock)
    def test_raw_call(self, m_req):
        api = Client(ENDPOINT, CLIENT_ID, CLIENT_SECRET)
        r = api.raw_call(FAKE_METHOD, FAKE_PATH, None)
        self.assertEqual(r.txt, "Let's assume requests will return this")
