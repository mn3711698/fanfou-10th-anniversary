from leancloud import LeanCloudError
from flask import Blueprint
from flask import render_template
from flask import jsonify
from flask import request
from flask_login import login_required
from flask_login import current_user
import random
from models import FFProduct
from models import FFVote
from models import FFAuth
import const


main_view = Blueprint('main', __name__)


@main_view.route('/', methods=['GET'])
@main_view.route('/rank', methods=['GET'])
@login_required
def index():
    nickname = current_user.get('nickname')
    products = FFProduct.query.add_descending('vote').find()
    product_list = []
    voted = {}
    for product in products:
        image_list = []
        for image in product.get('images'):
            image_list.append(image)
        product_item = {'id': product.id,
                        'name': product.get('name'),
                        'desc': product.get('intro'),
                        'vote': product.get('vote'),
                        'user': {'nickname': product.get('authorName'),
                                 'avatar': product.get('authorAvatar')},
                        'img': image_list}
        product_list.append(product_item.copy())

        ff_vote = None
        try:
            ff_vote = FFVote.query.equal_to('authUser', current_user).equal_to('targetProduct', product).first()
        except LeanCloudError as _:
            pass
        voted[product.id] = True if ff_vote else False

    list_type = 'rank'
    if not request.path.startswith('/rank'):
        random.shuffle(product_list)
        list_type = 'index'

    return render_template('index.html',
                           data=product_list,
                           voted=voted,
                           nickname=nickname,
                           list_type=list_type)


@main_view.route('/products/<string:product_id>/<string:action>', methods=['POST'])
@login_required
def vote(product_id, action):
    ff_vote_count = FFVote.query.equal_to('authUser', current_user).count()
    if ff_vote_count >= const.VOTE_LIMIT:
        return jsonify({'success': False,
                        'error': '最多只能投' + str(const.VOTE_LIMIT) + '个'})

    try:
        ff_product = FFProduct.query.get(product_id)
    except LeanCloudError as _:
        return jsonify({'success': False,
                        'error': '没有查询到该作品'})

    try:
        ff_auth = FFAuth.query.get(current_user.id)
    except LeanCloudError as _:
        return jsonify({'success': False,
                        'error': '没有查询到该用户'})

    ff_vote = None
    try:
        ff_vote = FFVote.query.equal_to('authUser', ff_auth).equal_to('targetProduct', ff_product).first()
    except LeanCloudError as _:
        pass

    if action == 'vote':
        if ff_vote:
            return jsonify({'success': False,
                            'error': '已经投过'})
        try:
            ff_vote = FFVote()
            ff_vote.set('authUser', ff_auth)
            ff_vote.set('targetProduct', ff_product)
            ff_vote.save()
        except LeanCloudError as _:
            return jsonify({'success': False,
                            'error': '写入数据库失败'})
        vote_count = ff_product.get('vote') + 1
        ff_product.set('vote', vote_count)
        ff_product.save()
        return jsonify({'success': True,
                        'error': ''})

    if action == 'undo':
        if not ff_vote:
            return jsonify({'success': True,
                            'error': ''})
        try:
            ff_vote.destroy()
            vote_count = ff_product.get('vote') - 1
            ff_product.set('vote', vote_count)
            ff_product.save()
        except LeanCloudError as _:
            return jsonify({'success': False,
                            'error': '删除失败'})
        return jsonify({'success': True,
                        'error': ''})
