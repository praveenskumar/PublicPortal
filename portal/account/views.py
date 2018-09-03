import re

from flask import (Blueprint, Markup, flash, jsonify, redirect, request,
                   session, url_for)
from flask_admin.base import expose
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_babelex import gettext
from flask_sqlalchemy_cache import FromCache
from flask_user import current_user, login_required
from jinja2 import contextfunction
from portal.account.models import AttributeManagerSingleton as AMS
from portal.account.models import Account, AccountStatus, AccountStatusHelper
from portal.account.utils import AccessHistory, ReplacementBank, VersionHistory
from portal.account.widgets import (AttentionWidget, ExpiringWidget,
                                    NotUpdatedTodayWidget)
from portal.admin.utils import (AccessControlView, AuthorizationRequiredView,
                                TimeTrackedModelView)
from portal.cache import cache
from portal.permission.forms import PermissionCheckingAccountForm
from portal.user import RolesEnum
from portal.user.models import Role, User, UsersRoles
from portal.utils.EnumRelated import EnumSQLAModelView
from portal.vps.models import Vps
from sqlalchemy import and_
from wtforms.validators import ValidationError, required

from .HandsonUploader import HandsonUploader

# This blueprint serves as a router
account_blueprint = Blueprint('account', __name__, template_folder='templates')


@account_blueprint.route('/', defaults={'path': ''}, methods=['GET'])
@account_blueprint.route('/<path:path>', methods=['GET'])
@login_required
def route(path):
    """Routes the user to the correct AccountModelView. i.e.,
    /account/ -> /admin_account/ (for admin)
    /account/ -> /technician_account/ (for technician)

    TODO:
    - figure out how to have GET arguments working (**request.args?)
    - figure out if this will work for POST
    """
    assert len(current_user.roles) == 1, 'Only 1 role per user allowed'
    if request.args:
        raise ValueError('Router currently does not support request.args')

    role = current_user.roles[0].name
    new_path = '%s_account/%s' % (role, path)
    return redirect(new_path)


def adwords_id_validator(form, field):
    if not re.match('^[0-9]{3}-[0-9]{3}-[0-9]{4}$', field.data):
        raise ValidationError(gettext('Adwords ID must be in the format of 123-456-7890.'))


def status_validator(form, field):
    if field.data in [AccountStatus.APPEAL_REQUESTED,
                      AccountStatus.APPEAL_SUBMITTED, AccountStatus.DISAPPROVED]:
        raise ValidationError('Deprecated. Please use only '
                              'Uninitialized, Unassigned, Reserved, Active, Suspended & Abandoned.')


def VPS_max_count_validator(form, field):
    """This does not affect Eve because Eve doesn't use this form. However, no manual edits will be
    possible via this form.
    """
    VPSs = field.data
    for vps in VPSs:
        # If this account already belongs to an MCC that is registered with this VPS,
        # then we will allow it to bypass this rule.
        existing_logins = set([account.login for account in vps.accounts])
        if form.login.data not in existing_logins:
            if len(vps.accounts) > 10:
                raise ValidationError('%s overloaded: Use another one.' % vps)


class AbstractAccountModelView(EnumSQLAModelView):
    """Use this to implement functionalities across all AccountModelViews.

    You must override the attribute `role` for this to work.

    Regarding providing data for index_view's DataTable, we will not be using the
    native export in flask-admin because it sends the file as an attachment and
    doesn't allow additional info such as column data to be sent over.
    """

    role = None         # This must be overriden!

    page_size = False

    can_view_details = True

    details_template = 'account/details.html'

    #
    # List View
    #

    list_template = 'account/list.html'

    column_type_formatters = TimeTrackedModelView.column_type_formatters
    column_type_formatters.update({
        float: lambda view, value: '%.2f' % value,
        bool: lambda view, value: Markup('Yes' if value else 'No')
    })

    column_type_formatters_export = column_type_formatters

    column_sortable_list = ()
    column_default_sort = ('updated_at', True)

    def status_formatter(view, context, model, name):
        return AccountStatusHelper.translate(getattr(model, name))

    column_formatters = {
        'status': status_formatter,
    }

    @contextfunction
    def get_list_value(self, context, model, name):
        if name == 'VPSs':
            return model.VPSs_jinja
        else:
            return super(AbstractAccountModelView, self).get_list_value(context, model, name)

    #
    # Forms
    #

    form_base_class = PermissionCheckingAccountForm

    form_args = {
        'adwords_id': {
            'description': '123-456-7890',
            'validators': [required(), adwords_id_validator],
        },
        'status': {
            'validators': [required(), status_validator],
        },
        'vendor': {
            'validators': [required()],
        },
        'login': {
            'validators': [required()],
        },
        'password': {
            'validators': [required()],
        },
        'VPSs': {
            'validators': [required(), VPS_max_count_validator],
        }
    }

    form_excluded_columns = ['versions']

    def create_form(self):
        return self._filtered_form(super(AbstractAccountModelView, self).create_form())

    def edit_form(self, obj):
        return self._filtered_form(super(AbstractAccountModelView, self).edit_form(obj))

    def _filtered_form(self, form):
        """Need to perform attribute check for ACL.
        """
        if hasattr(form, 'client'):
            form.client.query_factory = self._get_clients_only
        if hasattr(form, 'vps'):
            form.vps.query_factory = self._get_alive_vps_only
        return form

    def _get_clients_only(self):
        return User.query.join(UsersRoles).join(Role).filter(
            and_(User.id == UsersRoles.user_id,
                 UsersRoles.role_id == Role.id,
                 Role.name == RolesEnum.CLIENT.value)).all()

    def _get_alive_vps_only(self):
        return Vps.query.filter(Vps.is_deleted.isnot(True))\
            .order_by(Vps.created_at.desc()).all()

    def get_save_return_url(self, model, is_created=False):
        return self.get_url('.details_view', id=model.id)

    def __init__(self, *args, **kwargs):
        """Setting columns must take place before super.__init__.
        """
        self.column_labels = AMS.get_list_view_column_labels(self.role)

        self.column_list = AMS.get_list_view_columns(self.role)
        self.column_export_list = AMS.get_list_view_columns(self.role)
        self.column_details_list = AMS.get_list_view_columns(self.role)

        self.column_editable_list = AMS.get_list_view_editable_columns(self.role)
        self.form_columns = AMS.get_all_editable_columns(self.role)

        super(AbstractAccountModelView, self).__init__(*args, **kwargs)

    def get_account_histories(self, account_id):
        model = self.get_one(account_id)
        histories = []
        for version in model.versions:
            history = VersionHistory(version, self.role)
            if history.can_render():
                histories.append(history)

        for access in model.accesses:
            history = AccessHistory(access)
            if history.can_render():
                histories.append(history)

        histories = sorted(histories)
        return histories

    @expose('/<regex("[0-9]{3}-[0-9]{3}-[0-9]{4}"):adwords_id>/')
    def redirect_to_details_views(self, adwords_id):
        account = Account.query.filter(Account.adwords_id == adwords_id).one_or_none()
        if not account:
            flash('Account not found.', 'error')
            return redirect(url_for('user.member_page'))
        return redirect(url_for('.details_view', id=account.id))

    def render(self, template, **kwargs):
        """Passing in additional arguments to self.render. Useful for adding more
        visual elements to jinja.

        For ClientAccountModelView, we need to have the following order for class
        declaration:
            1. AccessControlView,
            2. AbstractAccountModelView,
            3. AuthorizationRequiredView

        The methods: index_view, details_view, delete_view, edit_view for AccessControlView
        **must** be the final overrides to enforce ACL.
        """
        if template == 'account/important_list.html':
            kwargs['expiring_widget'] = ExpiringWidget()
            kwargs['not_updated_today_widget'] = NotUpdatedTodayWidget()
            kwargs['attention_widget'] = AttentionWidget()

        if template.endswith('list.html'):
            kwargs['replacement_bank'] = ReplacementBank()
            kwargs['AccountStatusHelper'] = AccountStatusHelper
            kwargs['locale'] = session.get('lang', 'en')
        elif template.endswith('details.html'):
            id = get_mdict_item_or_list(request.args, 'id')
            if id:
                kwargs['histories'] = self.get_account_histories(id)

        return super(AbstractAccountModelView, self).render(template, **kwargs)

    #
    # Rendering JSON data for Data Tables in list_view.
    #

    def get_summary_positions(self):
        ret = []
        for i, (key, label) in enumerate(self.get_dt_columns(True)):
            if key in ['spent_in_hkd', 'remaining_in_hkd']:
                ret.append(i)
        return ret

    def get_dt_columns(self, with_non_data_columns=False):
        """Returns [(key, label), ..]
        """
        if with_non_data_columns:
            actions, actions_confirmation = self.get_actions_list()
            if actions:
                return [('checkbox', ''), ('row_actions', 'Actions')] + self._export_columns
            else:
                return [('row_actions', 'Actions')] + self._export_columns

        return self._export_columns

    def get_dt_columns_jinja(self, with_non_data_columns=False):
        """Returns [(key, label, pos), ..]
        """
        def _format(start):
            return [(key, label, i) for i, (key, label) in enumerate(self._export_columns, start)]

        if with_non_data_columns:
            actions, actions_confirmation = self.get_actions_list()
            if actions:
                return [('checkbox', '', 0), ('row_actions', 'Actions', 1)] + _format(2)
            else:
                return [('row_actions', 'Actions', 0)] + _format(1)

        return _format(0)

    def get_column_defs(self):
        """Returns column definitions which includes width.
        Doing this in CSS is impossible.
        """
        SHORT = {'width': '6em'}
        MEDIUM = {'width': '9em'}
        LONG = {'width': '20em'}
        mapping = {
            'adwords_id': SHORT,
            'batch': SHORT,
            'status': {'width': '8em'},
            'nickname': MEDIUM,
            'login': MEDIUM,
            'last_visited_by_eve': MEDIUM,
            'password': MEDIUM,
            'vendor': LONG,
            'internal_comment': LONG,
            'external_comment': LONG,
            'clients_allowed': LONG,
            'VPSs': MEDIUM,
        }

        ret = []
        for i, c in enumerate(self.get_dt_columns(True)):     # ref to column_number
            key = c[0]
            base = {'targets': i, 'name': key}
            if key in mapping:
                base.update(mapping[key])
            ret.append(base)
        return ret

    def get_dt_filters(self):
        """Provides YADCF options to be included in index_view_data json.

        Note that there is a bug with X-Editable and Select2 filters. Select2
        filters cannot different solely just on text alone. Hence you will see
        multiple entries of the same status.
        """
        settings = {
            'client_id': {},
            'account_budget': {'filter_type': 'range_number'},
            'status': {
                'filter_type': "multi_select",
                'select_type': 'chosen',
            },
            'vendor': {},
            'vps': {},
        }
        ret = []
        for i, c in enumerate(self.get_dt_columns(True)):     # ref to column_number
            key = c[0]
            if key in settings:

                # X-editiable elements will require this
                if key in AMS.get_list_view_editable_columns(self.role):
                    settings[key]['column_data_type'] = 'html'

                ret.append(dict(column_number=i,
                                filter_container_id='filter_container_%s' % i,
                                label=c[1],
                                **settings[key]))
        return ret

    def get_status_position(self):
        for i, c in enumerate(self.get_dt_columns(True)):
            if c[0] == 'status':
                return i + 1
        raise Exception('"status" position cannot be determined')

    @expose('/index_view_data/')
    def index_view_data(self):
        """Provides data for index_view to be used with DataTables.
        """
        response_raw = {
            'filters': self.get_dt_filters(),
            'status_pos': self.get_status_position(),
            'summary_pos': self.get_summary_positions(),
            'columnDefs': self.get_column_defs(),
        }
        return jsonify(response_raw)

    def get_query(self):
        """Using flask-sqlalchemy-cache now
        """
        return self.session.query(self.model).options(FromCache(cache))


class AdminAccountModelView(AbstractAccountModelView,
                            AuthorizationRequiredView, HandsonUploader):

    list_template = 'account/important_list.html'

    role = RolesEnum.ADMIN.value

    def get_accessible_roles(self):
        return [RolesEnum.ADMIN.value]


class TechnicianAccountModelView(AbstractAccountModelView,
                                 AuthorizationRequiredView, HandsonUploader):

    list_template = 'account/important_list.html'

    role = RolesEnum.TECHNICIAN.value

    can_delete = False
    can_create = False
    can_edit = True

    def get_accessible_roles(self):
        return [RolesEnum.TECHNICIAN.value, RolesEnum.ADMIN.value]


class SupportAccountModelView(AbstractAccountModelView, AuthorizationRequiredView):

    role = RolesEnum.SUPPORT.value

    can_delete = False
    can_create = False
    can_edit = True

    def get_accessible_roles(self):
        return [RolesEnum.SUPPORT.value, RolesEnum.ADMIN.value]


class ClientAccountModelView(AccessControlView,
                             AbstractAccountModelView, AuthorizationRequiredView):

    role = RolesEnum.CLIENT.value

    can_delete = False
    can_edit = True
    can_create = False

    access_attribute = 'client_id'        # AccessControlView

    def get_accessible_roles(self):
        return [RolesEnum.CLIENT.value, RolesEnum.ADMIN.value]
