
import unittest

from flask import get_flashed_messages
from portal.factory import create_app


class AuthTestConfig(object):
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    LOGIN_DISABLED = False
    SERVER_NAME = 'Testing'
    SECRET_KEY = 'secret'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    REFRESH_GOOGLE_TOKEN = False


class DebugTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(AuthTestConfig)
        self.client = self.app.test_client(use_cookies=True)

    def test_with(self):
        with self.client:
            self.client.get('/user/member')
            ms = get_flashed_messages()
            assert len(ms) == 1
            assert ms[0].startswith('You must be signed in to access ')

    @unittest.skip('TODO')
    def test_push(self):
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.client.get('/user/member')
        ms = get_flashed_messages()
        assert len(ms) == 1
        assert ms[0].startswith('You must be signed in to access ')


if __name__ == "__main__":
    unittest.main()
