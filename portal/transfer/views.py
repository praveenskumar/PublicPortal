

from flask_admin.contrib.sqla.filters import FilterLike
from flask_babelex import lazy_gettext
from portal.admin.utils import AuthorizationRequiredView, TimeTrackedModelView
from portal.bank_account.models import BankAccount
from portal.user import RolesEnum
from portal.utils import ColumnMetaContainer

CMC = ColumnMetaContainer()
CMC.add(name='date', label=lazy_gettext('Date'),
                description=lazy_gettext('Date shown on the check.'))
CMC.add(name='bank_account', label=lazy_gettext('Bank Account'))
CMC.add(name='counter_party', label=lazy_gettext('Counter Party'),
                description=lazy_gettext('If payment, this is "origin". If refund, this is "destination".'))
CMC.add(name='is_refund', label=lazy_gettext('Refund?'))
CMC.add(name='gross', label=lazy_gettext('Gross Amount'),
                description=lazy_gettext('This is the number that appears on the check. If refund, use negative.'))
CMC.add(name='net', label=lazy_gettext('Net Amount'),
                description=lazy_gettext('Total amount we can spend. This is typically gross - service fee.'))
CMC.add(name='currency', label=lazy_gettext('Currency'),
                description=lazy_gettext('USD, HKD, RMB, SGD'))
CMC.add(name='exchange_rate', label=lazy_gettext('Exchange Rate'),
                description=lazy_gettext('X * Exchange Rate = X in HKD'))
CMC.add(name='notes', label=lazy_gettext('Notes'))


class TransferModelView(TimeTrackedModelView, AuthorizationRequiredView):

    list_template = 'transfer/list.html'

    page_size = 100

    def get_accessible_roles(self):
        return [RolesEnum.ADMIN.value]

    can_delete = True

    column_editable_list = ('bank_account', 'net', )

    column_sort = ('date', False)

    column_list = CMC.get_column_list()

    column_labels = CMC.get_column_labels()

    column_filters = [FilterLike(BankAccount.name,
                                                             lazy_gettext('Bank Account'))]

    column_descriptions = CMC.get_column_descriptions()

    form_args = CMC.get_form_args()

