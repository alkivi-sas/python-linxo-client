python-linxo-client
==========================


![PyPI](https://img.shields.io/pypi/v/linxo.svg)
![PyPI](https://img.shields.io/pypi/status/linxo.svg)
[![Build Status](https://travis-ci.org/alkivi-sas/python-linxo-client.svg?branch=master)](https://travis-ci.org/alkivi-sas/python-linxo-client)
[![Requirements Status](https://requires.io/github/alkivi-sas/python-linxo-client/requirements.svg?branch=master)](https://requires.io/github/alkivi-sas/python-linxo-client/requirements/?branch=master)

Python client for [Linxo API](https://www.linxo.com)

Installation
============

The python wrapper works with Python 2.6+ and Python 3.2+.

The easiest way to get the latest stable release is to grab it from [pypi](https://pypi.python.org/pypi/linxo>) using ``pip``.

```bash
pip install linxo-client
```

Alternatively, you may get latest development version directly from Git.

```
pip install -e git+https://github.com/alkivi-sas/python-linxo-client.git#egg=linxo
```

Configuration
=============

Create a linxo.conf. They are parsend in that order.

```
# Current directory
./linxo.conf

# Home directory
~/.linxo.conf

# Global
/etc/linxo.conf
```


The file should contains client_id and client_secret with a fake access and refresh_token. You can obtain client_id and client_secret by contacting Linxo.

```ini
[default]
endpoint = prod

[prod]
client_id = dazjdkazldnoiazd,azldaz
client_secret = dazdazdza
access_token = fake for now
refresh_token = fake for now````

Next step is to generate a token



```python
# -*- encoding: utf-8 -*-
import linxo

# create a client using configuration
client = linxo.Client()

# Request token
valid_scopes = [
        'accounts_manage',
        'accounts_read',
        'connections_manage',
        'connections_sync',
        'transactions_read',
        'users_create']
client.generate_token(scopes=['transactions_read'])
```

Execute the code, you will be asked to login to linxo and you will be redirected to localhost.
Copy the code part, and the token will be save to your configuration file automatically.

Usage
=====
```python
# -*- encoding: utf-8 -*-
import linxo

client = linxo.Client()
client.get('/transactions')
```

Documentation
=============
The api documentation is [available here](https://sandbox-api.linxo.com/v2/documentation/).
