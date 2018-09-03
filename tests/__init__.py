import unittest

from portal.config import TestingConfig
from portal.factory import create_app
from portal.models import db


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.client = self.app.test_client()
        self.db = db

        self.app_context.push()
        self.db.create_all()

    def tearDown(self):
        self.db.session.remove()
        self.db.drop_all()
        self.app_context.pop()

