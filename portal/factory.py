import pytz
from flask import Flask, redirect, request, session, url_for
from flask._compat import text_type
from flask.json import JSONEncoder as BaseEncoder
from flask_admin import helpers as admin_helpers
from flask_admin import Admin
from flask_admin.base import MenuLink
from flask_babelex import Babel, lazy_gettext
from flask_compress import Compress
#from flask_debugtoolbar import DebugToolbarExtension
from flask_login import current_user
from flask_migrate import Migrate
from flask_user import SQLAlchemyAdapter, UserManager
from flask_user.access import is_authenticated
from portal.config import HerokuConfig
from portal.user import RolesEnum
from speaklater import _LazyString
from sqlalchemy import MetaData
from werkzeug.routing import BaseConverter

from .cache import cache
from .models import db


class RoleBasedMenuLink(MenuLink):

    def __init__(self, *args, **kwargs):
        self.roles = kwargs.pop('roles')
        super(RoleBasedMenuLink, self).__init__(*args, **kwargs)

    def is_accessible(self):
        if not is_authenticated():
            return False
        if current_user.has_role(*self.roles):
            return True
        return False


class UsernameBasedMenuLink(MenuLink):
    """Limits accessibility to people based on username.
    """
    def __init__(self, *args, **kwargs):
        self.usernames = kwargs.pop('usernames')
        super(UsernameBasedMenuLink, self).__init__(*args, **kwargs)

    def is_accessible(self):
        if not is_authenticated():
            return False
        if current_user.username in self.usernames:
            return True
        return False


def create_app(config, register_blueprints=True):
    app = Flask(__name__)
    app.config.from_object(config)

    convention = {
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
    MetaData(naming_convention=convention)
    db.init_app(app)

    #app.config['PROFILE'] = True
    #app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])

    # This needs to be after db is instantiated for migrate to discover
    from portal.user.models import Role, User
    from portal.account.models import Account
    from portal.vps.models import Vps
    from portal.vendor.models import Vendor
    from portal.transfer.models import Transfer
    from portal.bank_account.models import BankAccount
    from portal.permission.models import Permission
    Migrate(app, db)

    db_adapter = SQLAlchemyAdapter(db, User)
    UserManager(db_adapter, app)

    Compress(app)

    #DebugToolbarExtension(app)

    cache.init_app(app, config={'CACHE_TYPE': 'simple'})

    babel = Babel(app)
    # Monkeypatching Flask-babel
    babel.domain = 'flask_user'
    babel.translation_directories = 'translations'
    # All the translation should be done using Flask_Babelex's lazy_gettext as
    # opposed to flask_admin.babel's. The latter is referencing the domain
    # flask_admin.

    @babel.localeselector
    def get_locale():
        if request.args.get('lang'):
            session['lang'] = request.args.get('lang')
        return session.get('lang', 'en')

    class JSONEncoder(BaseEncoder):
        """so/questions/26124581/flask-json-serializable-error-because-of-flask-babel
        """
        def default(self, o):
            if isinstance(o, _LazyString):
                return text_type(o)
            return BaseEncoder.default(self, o)

    app.json_encoder = JSONEncoder

    @app.route('/')
    def default_page():
        if is_authenticated():
            return redirect(url_for('user.member_page'))
        return redirect(url_for('user.home_page'))

    def get_account_view_endpoint(suffix=None):
        """Returns 'ROLE_account.X' based on current_user
        """
        if not is_authenticated():
            raise Exception("Attempt to call get_account_view_endpoint without authentication")

        assert len(current_user.roles) == 1, 'User has more than 1 role!'
        if suffix:
            return '%s_account.%s' % (current_user.roles[0].name, suffix)
        return '%s_account' % current_user.roles[0].name

    class RegexConverter(BaseConverter):
        def __init__(self, url_map, *items):
            super(RegexConverter, self).__init__(url_map)
            self.regex = items[0]

    app.url_map.converters['regex'] = RegexConverter

    @app.context_processor
    def inject_admin_views():
        return dict(is_heroku=issubclass(config, HerokuConfig),     # isinstance doesn't work
                    admin_view=root.index_view, h=admin_helpers, get_url=url_for,
                    get_account_view_endpoint=get_account_view_endpoint)

    @app.template_filter()
    def format_currency(value):
        try:
            return "{:,.2f}".format(value)
        except ValueError:
            return value

    @app.template_filter()
    def to_hktz(value):
        if value:
            return value.astimezone(pytz.timezone('Asia/Hong_Kong'))

    @app.template_filter()
    def format_datetime(value):
        if value:
            return value.strftime('%m/%d %H:%M')

    if register_blueprints:     # prevent cyclical imports
        from portal.user.views import user_blueprint
        from portal.access.views import access_blueprint
        from portal.api.eve import eve_blueprint
        from portal.api.prometheus import prometheus_blueprint

        app.register_blueprint(user_blueprint, url_prefix='/user')
        app.register_blueprint(access_blueprint, url_prefix='/access')
        app.register_blueprint(eve_blueprint, url_prefix='/eve')
        app.register_blueprint(prometheus_blueprint, url_prefix='/prometheus')

        root = Admin(app, name='Portal', url='/', template_mode='bootstrap3')

        root.add_menu_item(RoleBasedMenuLink(name=lazy_gettext('Budget'),
                                             endpoint='user.budget',
                                             roles=[RolesEnum.CLIENT.value]))
        root.add_menu_item(RoleBasedMenuLink(name=lazy_gettext('Appointments'),
                                             endpoint='user.appointments',
                                             roles=[RolesEnum.CLIENT.value]))

        from portal.admin.views import UserModelView, RoleModelView
        root.add_view(UserModelView(User, db.session,
                                    category=lazy_gettext('User'), endpoint='admin_user'))
        root.add_view(RoleModelView(Role, db.session,
                                    category=lazy_gettext('User'), endpoint='admin_role'))

        from portal.account.views import account_blueprint, AdminAccountModelView, \
            TechnicianAccountModelView, SupportAccountModelView, ClientAccountModelView
        app.register_blueprint(account_blueprint, url_prefix='/account')

        ac = lazy_gettext('Account')

        root.add_view(AdminAccountModelView(
            Account, db.session, category=ac,
            name=lazy_gettext('Account (Admin)'), endpoint='admin_account'))
        root.add_view(SupportAccountModelView(
            Account, db.session, category=ac,
            name=lazy_gettext('Account (Support)'), endpoint='support_account'))
        root.add_view(TechnicianAccountModelView(
            Account, db.session, category=ac,
            name=lazy_gettext('Account (Technician)'), endpoint='technician_account'))
        root.add_view(ClientAccountModelView(
            Account, db.session, category=ac,
            name=lazy_gettext('Account (Client)'), endpoint='client_account'))

        root.add_link(UsernameBasedMenuLink(
            name=lazy_gettext('Batch Add'), category=ac,
            url='/account/handson_batch', usernames=['vincent', 'kevin', 'liang', 'bang']))

        from portal.vps.views import VpsModelView
        c = lazy_gettext('Vps')
        v = VpsModelView(Vps, db.session, endpoint='vps', category=c)
        root.add_view(v)
        root.add_link(RoleBasedMenuLink(
            name=lazy_gettext('Create'), category=c,
            endpoint='vps.create_view', roles=v.get_accessible_roles()))

        c = lazy_gettext('Vendor')
        from portal.vendor.views import VendorModelView
        v = VendorModelView(Vendor, db.session, endpoint='vendor', category=c)
        root.add_view(v)

        from portal.permission.views import PermissionModelView
        v = PermissionModelView(Permission, db.session, endpoint='permission', category=c)
        root.add_view(v)

        c = lazy_gettext('Finance')
        from portal.bank_account.views import BankAccountModelView
        v = BankAccountModelView(BankAccount, db.session, endpoint='bank_account', category=c)
        root.add_view(v)

        from portal.transfer.views import TransferModelView
        v = TransferModelView(Transfer, db.session, endpoint='transfer', category=c)
        root.add_view(v)

    return app
