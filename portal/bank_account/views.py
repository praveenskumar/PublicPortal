from flask_admin.model.template import macro
from flask_babelex import lazy_gettext as lg
from wtforms.validators import required

from portal.admin.utils import AuthorizationRequiredView, TimeTrackedModelView
from portal.user import RolesEnum
from portal.utils import ColumnMetaContainer

CMC = ColumnMetaContainer()
CMC.add(name='name', label=lg('Bank Account Name'))
CMC.add(name='details', label=lg('Bank Account Details'),
        description=lg('Include SWIFT, Intermediate Bank Information, USD/HKD account numbers, etc.')) # noqa
CMC.add(name='vendors', label=lg('Vendors'),
        description=lg('Select Multiple if necessary'))
CMC.add(name='transfer_count', label=lg('Transfers Count'),
        description=lg('Number of transfers associated with this Bank Account.'))
CMC.add(name='total_sent_in_hkd', label=lg('Total Sent HKD'),
        description=lg('Total HKD sent to this Bank Account.'))
CMC.add(name='total_spent_in_hkd', label=lg('Total Spent HKD'),
        description=lg('Total HKD spent by Adword Accounts associated to this to this Bank Account.')) # noqa
CMC.add(name='total_remaining_in_hkd', label=lg('Total Remaining HKD'),
        description=lg('Total HKD remaining in all Adwords Accounts associated to this Bank Account.')) # noqa
CMC.add(name='total_outstanding_in_hkd', label=lg('Total Outstanding HKD'),
        description=lg('Sent - (Spent + Remaining)'))


_column_list = CMC.get_column_list()
_column_list.remove('details')

_form_args = CMC.get_form_args()
_form_args['name']['validators'] = [required()]
_form_args['details']['validators'] = [required()]


class BankAccountModelView(TimeTrackedModelView, AuthorizationRequiredView):

    list_template = 'bank_account/list.html'

    column_default_sort = 'name'

    page_size = 100

    can_delete = True

    can_view_details = True

    def get_accessible_roles(self):
        return [RolesEnum.ADMIN.value]

    form_args = _form_args

    column_descriptions = CMC.get_column_descriptions()

    column_list = _column_list

    column_labels = CMC.get_column_labels()

    # NOTE: Don't touch encode at all and delegate to Markup

    column_formatters = {
        'vendors': macro('render_vendors'),
    }
