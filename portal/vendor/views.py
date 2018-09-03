import re

from flask_babelex import lazy_gettext as lg
from flask_babelex import gettext
from portal.admin.utils import AuthorizationRequiredView, TimeTrackedModelView
from portal.user import RolesEnum
from portal.utils import ColumnMetaContainer
from portal.vendor.widgets import VendorMCCWidget
from wtforms import validators
from wtforms.validators import ValidationError

CMC = ColumnMetaContainer()
CMC.add(name='is_active', label=lg('Is Active'),
        description=lg('Do we want to send new accounts to this vendor?'))
CMC.add(name='company_name', label=lg('Company Name'),
        description=lg('PAYMENT PROFILE name. NOT BILLING ACCOUNT NAME. This must match Google Adwords Billing page.'))
CMC.add(name='nickname', label=lg('Nickname'),
        description=lg('This is EXPOSED to the public. Pick something only us can understand.'))
CMC.add(name='contact_name', label=lg('Contact Name'))
CMC.add(name='payments_profile_id', label=lg('Payments Profile ID'),
        description=lg('Format: 1234-1234-1234'))
CMC.add(name='has_bank_account', label=lg('Has Bank Account'),
        description='If no bank account is associated, account spendings from this vendor will not be included in our revenue.')
CMC.add(name='bank_account', label=lg('Bank Account'))
CMC.add(name='service_fee', label=lg('Service Fee'),
        description=lg('How much deduction does this vendor charge? Include only variable fees and exclude any fixed retainers.'))
CMC.add(name='days_to_topup', label=lg('Topup Days'),
        description=lg('How many business days does it take to send money to our vendor and topup this account?')),

CMC.add(name='num_accounts_used', label=lg('Used'),
        description=lg('# of accounts that have been used'))
CMC.add(name='num_accounts_unused', label=lg('Unused'),
        description=lg('# of accounts that have not been used'))
CMC.add(name='num_accounts_total', label=lg('Total'),
        description=lg('Total # of accounts from this vendor'))

CMC.add(name='total_spent_in_hkd', label=lg('Total Spent HKD'))
CMC.add(name='payments_account_id', label=lg('Payments Accounts ID'),
        description=lg('Format: 1234-1234-1234-1234'))
CMC.add(name='notes', label=lg('Notes'))


def payments_profile_id_validator(form, field):
    if field.data and not re.match('^[0-9]{4}-[0-9]{4}-[0-9]{4}$', field.data):
        raise ValidationError(gettext('ID must be in the format of 1234-1234-1234.'))


def payments_account_id_validator(form, field):
    if field.data and not re.match('^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}$', field.data):
        raise ValidationError(gettext('ID must be in the format of 1234-1234-1234-1234'))


_form_args = CMC.get_form_args()
_form_args['service_fee']['validators'] = [validators.NumberRange(min=0, max=100)]
_form_args['payments_profile_id']['validators'] = [payments_profile_id_validator]
_form_args['payments_account_id']['validators'] = [payments_account_id_validator]


_column_list = CMC.get_column_list()
_column_list.remove('payments_account_id')
_column_list.remove('bank_account')


class VendorModelView(TimeTrackedModelView, AuthorizationRequiredView):

    def get_accessible_roles(self):
        return [RolesEnum.ADMIN.value]

    page_size = 100

    list_template = 'vendor/list.html'

    column_default_sort = ('is_active', True)

    column_list = _column_list

    column_editable_list = ('notes', )

    form_args = _form_args

    column_descriptions = CMC.get_column_descriptions()

    column_labels = CMC.get_column_labels()

    TimeTrackedModelView.form_excluded_columns.extend(['accounts', 'versions', 'transfers', 'permissions'])

    TimeTrackedModelView.column_type_formatters.update({
        float: lambda view, value: '{:,.2f}'.format(value),
    })

    def render(self, template, **kwargs):
        if template.endswith('list.html'):
            kwargs['vendor_mcc_widget'] = VendorMCCWidget()
        return super(VendorModelView, self).render(template, **kwargs)

