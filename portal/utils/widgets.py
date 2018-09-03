from flask_user import current_user


class Widget(object):
    """Class to encapsulate logic for ACL and rendering
    """
    def get_roles(self):
        """Roles that have the permission to render this widget.
        """
        raise NotImplementedError

    def is_accessible(self):
        assert len(current_user.roles) == 1, 'Only 1 role per user allowed'
        role = current_user.roles[0].name
        return role in [ role.value for role in self.get_roles() ]

    def get_data(self):
        """Returns the data needed to do the rendering
        """
        raise NotImplementedError
