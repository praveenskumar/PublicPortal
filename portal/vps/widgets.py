

from portal.user import RolesEnum
from portal.utils.widgets import Widget
from portal.vps.models import Vps


class ReleasableWidget(Widget):

    def get_roles(self):
        return [RolesEnum.ADMIN, RolesEnum.TECHNICIAN]

    def get_data(self):
        vpses = {}

        for vps in Vps.query.filter(Vps.is_deleted==False):
            # Not new and no more alive
            if len(vps.accounts) > 0 and vps.alive_count == 0:
                for account in vps.accounts:
                    vpses[vps.id] = vps

        return vpses
