# coding: utf-8

from leancloud import LeanCloudError
from flask import Blueprint
from flask import render_template
from flask import redirect
from flask import url_for
from flask import request
from flask import session
from flask_login import login_user
from flask_login import login_required
from flask_login import logout_user
import fanfou
import urllib
import json
from forms.auth import AuthForm
from models import FFAuth
import const
from requests_oauthlib import OAuth1Session


auth_view = Blueprint('auth', __name__)


@auth_view.route('/auth', methods=['GET', 'POST'])
def xauth():
    form = AuthForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data

            try:
                consumer = {'key': const.CONSUMER_KEY,
                            'secret': const.CONSUMER_SECRET}
                client = fanfou.XAuth(consumer, username, password)
                user_info = client.request('/users/show', 'POST')
                user_json = json.loads(user_info.read().decode('utf8'))
                nickname = user_json['screen_name']
                unique_id = user_json['unique_id']
                try:
                    ff_auth = FFAuth.query.equal_to('uniqueID', unique_id).first()
                except LeanCloudError as err:
                    if err.code == 101:
                        ff_auth = FFAuth()
                    else:
                        raise err
                token = client.oauth_token['key'].decode('utf-8')
                secret = client.oauth_token['secret'].decode('utf-8')
                ff_auth.set('uniqueID', unique_id)
                ff_auth.set('username', username)
                ff_auth.set('nickname', nickname)
                ff_auth.set('token', token)
                ff_auth.set('secret', secret)
                ff_auth.save()
                login_user(ff_auth, True)
                return redirect(url_for('main.index'))
            except LeanCloudError as _:
                error = '写入数据库失败'
            except urllib.error.HTTPError as _:
                error = '认证失败, 请输入正确的用户名和密码'
        else:
            error = '表单非法'
    else:
        error = session.get('error_msg', None)
        session['error_msg'] = None
    return render_template('auth.html',
                           form=form,
                           error=error)


@auth_view.route('/oauth')
def oauth_request():
    try:
        o = OAuth1Session(const.CONSUMER_KEY, const.CONSUMER_SECRET)
        req = o.fetch_request_token("http://fanfou.com/oauth/request_token")

        ov = request.url_root[:-1] + url_for(".oauth_verify")

        session['req'] = req
        auth = o.authorization_url("http://fanfou.com/oauth/authorize", oauth_callback=ov)
    except ValueError:
        session['error_msg'] = "网络连接错误，请重试！"
        return redirect(url_for('.xauth'))

    return redirect(auth)


@auth_view.route('/oauth_verify')
def oauth_verify():
    try:
        req = session['req']
        o = OAuth1Session(const.CONSUMER_KEY, const.CONSUMER_SECRET,
                          req['oauth_token'],
                          req['oauth_token_secret'], verifier=req['oauth_token'])
        ac = o.fetch_access_token("http://fanfou.com/oauth/access_token")
        session['req'] = ac
        user = o.get("http://api.fanfou.com/account/verify_credentials.json?mode=lite").json()
    except:
        session['error_msg'] = "验证失败，请重试！"
        return redirect(url_for('.xauth'))

    try:
        try:
            ff_auth = FFAuth.query.equal_to('uniqueID', user['unique_id']).first()
        except LeanCloudError as err:
            if err.code == 101:
                ff_auth = FFAuth()
        ff_auth.set('username', user['id'])
        ff_auth.set('nickname', user['name'])
        ff_auth.set('uniqueID', user['unique_id'])
        ff_auth.set('token', ac['oauth_token'])
        ff_auth.set('secret', ac['oauth_token_secret'])
        ff_auth.save()
    except LeanCloudError:
        session['error_msg'] = "写入数据库失败！"
        return redirect(url_for('.xauth'))
    login_user(ff_auth, True)
    return redirect(url_for('main.index'))


@auth_view.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
