import os


class Core(object):
    SECRET_KEY = 'somethingsecret'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    USER_APP_NAME = 'Client Portal'
    USER_ENABLE_CHANGE_PASSWORD = True
    USER_ENABLE_CHANGE_USERNAME = False
    USER_ENABLE_FORGOT_PASSWORD = False
    USER_ENABLE_LOGIN_WITHOUT_CONFIRM_EMAIL = False

    USER_ENABLE_EMAIL = False
    USER_ENABLE_CONFIRM_EMAIL = False
    USER_ENABLE_MULTIPLE_EMAILS = False
    USER_ENABLE_REGISTRATION = False

    USER_ENABLE_RETYPE_PASSWORD = True
    USER_ENABLE_USERNAME = True

    USER_AFTER_LOGIN_ENDPOINT = 'user.member_page'
    USER_AFTER_LOGOUT_ENDPOINT = 'user.home_page'

    COMPRESS_LEVEL = 9

    # Flask-babelex uses some custom Domain class which *requires* the
    # translation directory to be found at 'app_root/translations' for more
    # information see :get_translations, :domain in flask_babelex/__init__.py

    # Not needed for flask_babelex
    #BABEL_TRANSLATION_DIRECTORIES = '../translations'

    # Prometheus API
    PROMETHEUS_API_LOGIN = 'prometheus'
    WHALESMEDIA_USER_ID = 888

    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 86400
    CACHE_THRESHOLD = 999999


class DevelopmentConfig(Core):
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/portal'
    SQLALCHEMY_ECHO = False


class HerokuConfig(Core):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', None)


class TestingConfig(Core):
    SERVER_NAME = 'Testing'
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/portal_testing'
    SQLALCHEMY_ECHO = False
