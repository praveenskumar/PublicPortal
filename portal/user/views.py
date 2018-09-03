
from flask import Blueprint, render_template
from flask_user import current_user, login_required

from portal.account.widgets import (AccountHistoryWidget, ActiveAccountsWidget,
                                    AttentionWidget, ExpiringWidget,
                                    HighSpendWidget, NotUpdatedTodayWidget,
                                    RecentStatusChangeWidget, TotalSpendWidget)

user_blueprint = Blueprint('user', __name__, template_folder='templates')


@user_blueprint.route('/')
def home_page():
    return render_template('/user/home_page.html')


@user_blueprint.route('/member')
@login_required
def member_page():
    return render_template('/user/member_page.html',
                                                 attention_widget=AttentionWidget(),
                                                 account_history_widget=AccountHistoryWidget(),
                                                 active_accounts_widget=ActiveAccountsWidget(),
                                                 expiring_widget=ExpiringWidget(),
                                                 not_updated_today_widget=NotUpdatedTodayWidget(),
                                                 high_spend_widget=HighSpendWidget(),
                                                 total_spend_widget=TotalSpendWidget(),
                                                 recent_status_change_widget=RecentStatusChangeWidget())


@user_blueprint.route('/budget')
@login_required
def budget():
    content = "Your private budget sheet has not been created yet."
    if current_user.budget_url:
        content = "Please visit <a href='%s'>here</a> for your budget sheet" % current_user.budget_url
    return render_template('/user/empty.html', content=content)


@user_blueprint.route('/appointments')
@login_required
def appointments():
    content = """<iframe src="https://app.acuityscheduling.com/schedule.php?owner=14348735" width="100%" height="800" frameBorder="0"></iframe>
<script src="https://d3gxy7nm8y4yjr.cloudfront.net/js/embed.js" type="text/javascript"></script>"""
    return render_template('/user/empty.html', content=content)
