
import json

from flask import Blueprint, request
from flask_user import current_user, login_required
from portal.models import db

from .models import Access

access_blueprint = Blueprint('access', __name__, template_folder='templates')


"""
GET         /             Retrieve list of tasks            [NA]
POST        /             Create a new task
GET         /[id]     Retrieve a task                         [NA]
PUT         /[id]     Update an existing task         [NA]
DELETE    /[id]     Delete a task                             [NA]
"""

@access_blueprint.route('/', methods=['POST'])
@login_required
def create_view():
    account_id = request.form.get('account_id')
    if account_id is None:
        return (
            json.dumps({ 'success':False, 'message':'account_id is missing.' }),
            400,
            {'ContentType':'application/json'},
        )

    db.session.add(Access(user_id=current_user.id, account_id=account_id))
    db.session.commit()
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
