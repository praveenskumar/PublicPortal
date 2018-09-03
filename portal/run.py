import os

from portal.factory import create_app

from .config import DevelopmentConfig, HerokuConfig

if os.environ.get('HEROKU', False):
    app = create_app(HerokuConfig)
else:
    app = create_app(DevelopmentConfig)
