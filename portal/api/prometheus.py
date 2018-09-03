
from functools import wraps

from flask import Blueprint, Response, current_app, jsonify, request
from portal.account.models import Account
from portal.user.models import User

prometheus_blueprint = Blueprint('prometheus', __name__, template_folder='templates')


def check_auth(username, password):
    if username != current_app.config['PROMETHEUS_API_LOGIN']:
        return False

    user = User.query.filter(
        User.username == current_app.config['PROMETHEUS_API_LOGIN']).one()
    return current_app.user_manager.verify_password(password, user)


def basic_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return Response('Auth Required', 401,
                            {'WWW-Authenticate': 'Basic realm="Login Required"'})
        if check_auth(auth.username, auth.password):
            return f(*args, **kwargs)
        return Response('Incorrect Credentials', 401,
                        {'WWW-Authenticate': 'Basic realm="Incorrect Credentials"'})
    return decorated


@prometheus_blueprint.route('/account/list', methods=['GET'])
@basic_auth
def list_accounts():
    """Returns json of our accounts with the following fields:
    - adwords_id
    - status
    - total_spent_hkd
    - login (for MCC)
    - vps

    Example response:
    {
        '123-456-7890': {
                            'spent_in_hkd': 0,
                            'status': 'RESERVED',
                            'daily_budget': 0
                        },
        '234-678-8900': ...
    }
    """
    wm_id = current_app.config['WHALESMEDIA_USER_ID']
    ret = {}
    for account in Account.query.filter(Account.client_id >= wm_id):
        ret[account.adwords_id] = dict(
            status=str(account.status.name),
            daily_budget_in_hkd=round(account.daily_budget_in_hkd or 0, 2),
            spent_in_hkd=round(account.spent_in_hkd or 0, 2),
            login=account.login,
            vendor_nickname=account.vendor.nickname,
            vps=account.VPSs_jinja,
        )
    return jsonify(ret)
