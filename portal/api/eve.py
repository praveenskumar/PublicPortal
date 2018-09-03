import json
import locale
import re
from functools import wraps

from flask import Blueprint, Response, jsonify, request
from portal.account.models import Account
from portal.models import db
from portal.vps.models import Vps
from sqlalchemy.sql import func

eve_blueprint = Blueprint('eve', __name__, template_folder='templates')


def check_auth(username, password):
    vps = Vps.query.filter(Vps.api_key == username).first()
    if vps:
        return vps.api_secret == password


def basic_auth(f):
    """See http://flask.pocoo.org/snippets/8/
    """
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


@eve_blueprint.route('/version')
def get_version():
    return '0.3'


NUM_REGEX = re.compile(r'([0-9]{1,3}(,[0-9]{3})*(\.[0-9]+)?)')
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

UNLIMITED_SPENDING = "Unlimited spending"


def parse_currency(string):
    r = NUM_REGEX.split(string)
    try:
        return r[0]
    except:
        raise ValueError('Invalid data: %s' % repr(string))


def parse_numeral(string):
    if string in ["--", UNLIMITED_SPENDING, u'\xe2\x80\x94', u'\u2014']:
        return 0
    try:
        r = NUM_REGEX.split(string)
        return locale.atof(r[1])
    except:
        raise ValueError('Invalid data: %s' % repr(string))


@eve_blueprint.route('/account/update', methods=['POST'])
@basic_auth
def update_accounts():
    """
    If you are running Eve in a browser that is also logged into our system,
    the API call *will* include your personal cookies. This will result in
    transaction.user_id to be you as flask-login.current_user = you.

    TODO:
    1. decide on the right course of action when act does not exist
    2. decide on whether we want to check vendor info
    3. fix logging

    TESTING:
        - (Use Postman if possible)
        - Code below:
    """
    print 'json.dumps(request.data):', request.data

    dics = json.loads(request.data)
    if not dics:
        return jsonify(success=False, message='No data present.')

    updated = 0

    for dic in dics['response']:
        try:
            act = Account.query.filter(Account.adwords_id == dic['adwords_id']).one_or_none()
            if not act:
                print "Account contained in Eve not found in db: adwords_id:%s" % dic['adwords_id']
                continue

            # TODO 04/13/2018 - Disabling checking on api_key and secret due to lack
            # of manpower to go through our logs.
            #elif act not in vps.accounts:
            #    current_app.logger.warning(
            #        "Vps.api_key not authorized to modify account. "
            #        "status: %s, adwords_id:%s, vps.api_key:%s",
            #        act.status, dic['adwords_id'], vps.api_key)
            #    continue

            else:
                if dic['account_budget'] == UNLIMITED_SPENDING:
                    act.is_unlimited = True
                act.currency = parse_currency(dic['daily_budget'])
                act.account_budget = parse_numeral(dic['account_budget'])
                act.remaining_account_budget = parse_numeral(dic['remaining_account_budget'])
                act.daily_budget = parse_numeral(dic['daily_budget'])
                act.nickname = dic['nickname']
                act.last_visited_by_eve = func.now()
                db.session.add(act)
                db.session.commit()
                updated += 1
        except Exception, e:
            print 'Exception:', e,
            print 'Data:', dic
            db.session.rollback()
            continue

    return jsonify(success=True, updated_count=updated)
