"""
管理后台 API
"""
import json
import hashlib
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from models import db, MonitorSource, Policy, Category, KnowledgeItem, MonitorLog, User
from crawler import PolicyCrawler, compute_hash
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username, is_active=True).first()
        if user:
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            if user.password_hash == pw_hash:
                session['admin_logged_in'] = True
                session['admin_user'] = username
                from datetime import datetime
                user.last_login = datetime.utcnow()
                db.session.commit()
                return redirect(url_for('admin.dashboard'))
        flash('用户名或密码错误', 'danger')
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@login_required
def dashboard():
    """管理后台首页"""
    policy_count = Policy.query.count()
    source_count = MonitorSource.query.count()
    knowledge_count = KnowledgeItem.query.count()
    today_policies = Policy.query.filter(Policy.created_at >= db.func.date('now')).count()
    today_logs = MonitorLog.query.filter(MonitorLog.created_at >= db.func.date('now')).count()

    last_logs = MonitorLog.query.order_by(MonitorLog.created_at.desc()).limit(10).all()

    category_stats = db.session.query(
        MonitorSource.category, db.func.count(MonitorSource.id)
    ).group_by(MonitorSource.category).all()

    return render_template('admin/dashboard.html',
        policy_count=policy_count,
        source_count=source_count,
        knowledge_count=knowledge_count,
        today_policies=today_policies,
        today_logs=today_logs,
        last_logs=last_logs,
        category_stats=category_stats)


# ===== 数据源管理 =====

@admin_bp.route('/sources')
@login_required
def source_list():
    sources = MonitorSource.query.order_by(MonitorSource.category, MonitorSource.name).all()
    return render_template('admin/sources.html', sources=sources)


@admin_bp.route('/api/sources', methods=['POST'])
@login_required
def source_create():
    data = request.json
    source = MonitorSource(
        name=data['name'],
        url=data['url'],
        source_type=data.get('source_type', 'web'),
        category=data.get('category', '其他'),
        crawl_method=data.get('crawl_method', 'get'),
        selectors=data.get('selectors', '{}'),
        enabled=data.get('enabled', True),
    )
    db.session.add(source)
    db.session.commit()
    return jsonify({'success': True, 'id': source.id})


@admin_bp.route('/api/sources/<int:source_id>', methods=['PUT'])
@login_required
def source_update(source_id):
    source = MonitorSource.query.get_or_404(source_id)
    data = request.json
    for field in ['name', 'url', 'source_type', 'category', 'crawl_method', 'selectors', 'enabled']:
        if field in data:
            setattr(source, field, data[field])
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/sources/<int:source_id>', methods=['DELETE'])
@login_required
def source_delete(source_id):
    source = MonitorSource.query.get_or_404(source_id)
    db.session.delete(source)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/sources/<int:source_id>/crawl', methods=['POST'])
@login_required
def source_crawl(source_id):
    """手动触发单个数据源抓取"""
    source = MonitorSource.query.get_or_404(source_id)
    crawler = PolicyCrawler(db.session)
    crawler.crawl_source(source)
    return jsonify({'success': True, 'status': source.last_crawl_status})


# ===== 政策管理 =====

@admin_bp.route('/policies')
@login_required
def policy_list():
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('q', '')
    category = request.args.get('category', '')

    query = Policy.query
    if category:
        source_ids = [s.id for s in MonitorSource.query.filter_by(category=category).all()]
        if source_ids:
            query = query.filter(Policy.source_id.in_(source_ids))
    if keyword:
        query = query.filter(Policy.title.contains(keyword))

    query = query.order_by(Policy.created_at.desc())
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    categories = db.session.query(MonitorSource.category).distinct().all()
    category_list = [c[0] for c in categories if c[0]]

    return render_template('admin/policies.html',
        policies=pagination.items, pagination=pagination,
        categories=category_list, current_category=category, keyword=keyword)


@admin_bp.route('/api/policies/<int:policy_id>', methods=['PUT'])
@login_required
def policy_update(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    data = request.json
    for field in ['title', 'summary', 'content', 'tags', 'is_pinned', 'file_type']:
        if field in data:
            setattr(policy, field, data[field])
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/policies/<int:policy_id>', methods=['DELETE'])
@login_required
def policy_delete(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    db.session.delete(policy)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/policies/batch-delete', methods=['POST'])
@login_required
def policy_batch_delete():
    ids = request.json.get('ids', [])
    Policy.query.filter(Policy.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/policies/to-knowledge', methods=['POST'])
@login_required
def policy_to_knowledge():
    """将政策条目转为知识库条目"""
    policy_id = request.json.get('policy_id')
    category_id = request.json.get('category_id')
    policy = Policy.query.get_or_404(policy_id)

    item = KnowledgeItem(
        category_id=category_id,
        title=policy.title,
        content=policy.content or policy.summary or '',
        source=policy.authority or '自动采集',
        source_url=policy.url,
        tags=policy.tags,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'id': item.id})


# ===== 分类管理 =====

@admin_bp.route('/categories')
@login_required
def category_list():
    categories = Category.query.order_by(Category.sort_order).all()
    return render_template('admin/categories.html', categories=categories)


@admin_bp.route('/api/categories', methods=['POST'])
@login_required
def category_create():
    data = request.json
    cat = Category(
        name=data['name'],
        parent_id=data.get('parent_id'),
        sort_order=data.get('sort_order', 0),
        icon=data.get('icon', 'bi-folder'),
        description=data.get('description', ''),
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify({'success': True, 'id': cat.id})


@admin_bp.route('/api/categories/<int:cat_id>', methods=['PUT'])
@login_required
def category_update(cat_id):
    cat = Category.query.get_or_404(cat_id)
    data = request.json
    for field in ['name', 'parent_id', 'sort_order', 'icon', 'description']:
        if field in data:
            setattr(cat, field, data[field])
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/categories/<int:cat_id>', methods=['DELETE'])
@login_required
def category_delete(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.children:
        return jsonify({'success': False, 'message': '该分类下有子分类，不能删除'}), 400
    db.session.delete(cat)
    db.session.commit()
    return jsonify({'success': True})


# ===== 知识库管理 =====

@admin_bp.route('/knowledge')
@login_required
def knowledge_list():
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('q', '')
    cat_id = request.args.get('category_id', 0, type=int)

    query = KnowledgeItem.query
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    if keyword:
        query = query.filter(
            db.or_(KnowledgeItem.title.contains(keyword), KnowledgeItem.content.contains(keyword))
        )
    query = query.order_by(KnowledgeItem.updated_at.desc())
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    categories = Category.query.order_by(Category.sort_order).all()
    return render_template('admin/knowledge.html',
        items=pagination.items, pagination=pagination,
        categories=categories, current_category_id=cat_id, keyword=keyword)


@admin_bp.route('/api/knowledge', methods=['POST'])
@login_required
def knowledge_create():
    data = request.json
    item = KnowledgeItem(
        category_id=data['category_id'],
        title=data['title'],
        content=data.get('content', ''),
        source=data.get('source', ''),
        source_url=data.get('source_url', ''),
        tags=data.get('tags', ''),
        is_pinned=data.get('is_pinned', False),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'id': item.id})


@admin_bp.route('/api/knowledge/<int:item_id>', methods=['PUT'])
@login_required
def knowledge_update(item_id):
    item = KnowledgeItem.query.get_or_404(item_id)
    data = request.json
    for field in ['category_id', 'title', 'content', 'source', 'source_url', 'tags', 'is_pinned']:
        if field in data:
            setattr(item, field, data[field])
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/knowledge/<int:item_id>', methods=['DELETE'])
@login_required
def knowledge_delete(item_id):
    item = KnowledgeItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})


# ===== 全局抓取 =====

@admin_bp.route('/api/crawl-all', methods=['POST'])
@login_required
def crawl_all():
    crawler = PolicyCrawler(db.session)
    crawler.crawl_all_enabled()
    return jsonify({'success': True})


# ===== 统计API =====

@admin_bp.route('/api/stats')
@login_required
def api_stats():
    return jsonify({
        'policy_count': Policy.query.count(),
        'source_count': MonitorSource.query.count(),
        'knowledge_count': KnowledgeItem.query.count(),
        'today_policies': Policy.query.filter(Policy.created_at >= db.func.date('now')).count(),
    })
