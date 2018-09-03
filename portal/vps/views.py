from flask import Markup
from flask_babelex import lazy_gettext
from wtforms.fields import SelectField
from wtforms.validators import required
from wtforms_alchemy import Unique

from portal.admin.utils import (AccessControlView, AuthorizationRequiredView,
                                                                TimeTrackedModelView)
from portal.user import RolesEnum
from portal.utils import ColumnMetaContainer
from portal.utils.EnumRelated import EnumSQLAModelView
from portal.vps.models import Vps
from portal.vps.widgets import ReleasableWidget

CMC = ColumnMetaContainer()
CMC.add(name='name', label=lazy_gettext('Name'),
                description='AWS-JP-001')
CMC.add(name='is_deleted', label=lazy_gettext('Deleted?'),
                description=lazy_gettext('Has the VPS been deleted?'))
CMC.add(name='instance_id', label=lazy_gettext('Instance ID'),
                description=lazy_gettext('i-00166a8b8c34e7265'))
CMC.add(name='provider', label=lazy_gettext('Provider'),
                description=lazy_gettext('AWS/Aliyun/Digital Ocean'))
CMC.add(name='country', label=lazy_gettext('Country'),
                description=lazy_gettext('Hong Kong/Japan/China'))
CMC.add(name='ip_addr', label=lazy_gettext('Ip Address'),
                description=lazy_gettext('1.2.3.4'))
CMC.add(name='login', label=lazy_gettext('Login'),
                description=lazy_gettext('AWS default login: Administrator'))
CMC.add(name='password', label=lazy_gettext('Password'),
                description=lazy_gettext('AWS default password: qweASD123'))
CMC.add(name='api_key', label=lazy_gettext('API Key'),
                description=lazy_gettext('If changed please update on VPS\'s chrome extension'))
CMC.add(name='api_secret', label=lazy_gettext('API Secret'),
                description=lazy_gettext('If changed please update on VPS\'s chrome extension'))


_form_args = CMC.get_form_args()
_form_args['provider']['choices'] = [('AWS', 'AWS'), ('Aliyun', 'Aliyun')]
_form_args['country']['choices'] = [('Tokyo', 'Tokyo'), ('Hong Kong', 'Hong Kong'), ('Singapore', 'Singapore') ]
_form_args['instance_id']['validators'] = [required(), Unique(Vps.instance_id)]
_form_args['api_key']['validators'] = [required(), Unique(Vps.instance_id)]


class VpsModelView(TimeTrackedModelView, EnumSQLAModelView, AuthorizationRequiredView):

    def get_accessible_roles(self):
        return [RolesEnum.TECHNICIAN.value, RolesEnum.ADMIN.value]

    column_filters = ('is_deleted', 'provider')

    column_default_sort = ('updated_at', True)

    page_size = 50

    TimeTrackedModelView.form_excluded_columns.extend(['accounts'])

    column_list = CMC.get_column_list()

    column_labels = CMC.get_column_labels()

    form_args = _form_args

    form_overrides = {
        'provider': SelectField,
        'country': SelectField,
    }

    column_type_formatters = TimeTrackedModelView.column_type_formatters
    column_type_formatters.update({
        bool: lambda view, value: Markup('Yes' if value else 'No')
    })

    def render(self, template, **kwargs):
        if template.endswith('list.html'):
            kwargs['releasable_widget'] = ReleasableWidget()
        return super(VpsModelView, self).render(template, **kwargs)
