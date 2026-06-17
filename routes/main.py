"""
前端展示路由
"""
from flask import Blueprint, render_template, request, jsonify
from models import db, Policy, Category, KnowledgeItem, MonitorSource, MonitorLog

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """首页 - 仪表盘"""
    policy_count = Policy.query.count()
    source_count = MonitorSource.query.filter_by(enabled=True).count()
    knowledge_count = KnowledgeItem.query.count()
    category_count = Category.query.count()

    today_policies = Policy.query.filter(
        Policy.created_at >= db.func.date('now')
    ).count()

    recent_policies = Policy.query.order_by(
        Policy.is_pinned.desc(), Policy.created_at.desc()
    ).limit(10).all()

    recent_knowledge = KnowledgeItem.query.order_by(
        KnowledgeItem.is_pinned.desc(), KnowledgeItem.updated_at.desc()
    ).limit(6).all()

    recent_logs = MonitorLog.query.order_by(
        MonitorLog.created_at.desc()
    ).limit(8).all()

    return render_template('index.html',
        policy_count=policy_count,
        source_count=source_count,
        knowledge_count=knowledge_count,
        category_count=category_count,
        today_policies=today_policies,
        recent_policies=recent_policies,
        recent_knowledge=recent_knowledge,
        recent_logs=recent_logs)


@main_bp.route('/policies')
def policy_list():
    """政策列表页"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    keyword = request.args.get('q', '')

    query = Policy.query

    if category:
        source_ids = [s.id for s in MonitorSource.query.filter_by(category=category).all()]
        if source_ids:
            query = query.filter(Policy.source_id.in_(source_ids))

    if keyword:
        query = query.filter(
            db.or_(
                Policy.title.contains(keyword),
                Policy.summary.contains(keyword),
                Policy.content.contains(keyword),
                Policy.tags.contains(keyword)
            )
        )

    query = query.order_by(Policy.is_pinned.desc(), Policy.created_at.desc())
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    categories = db.session.query(MonitorSource.category).distinct().all()
    category_list = [c[0] for c in categories if c[0]]

    return render_template('policies.html',
        policies=pagination.items,
        pagination=pagination,
        categories=category_list,
        current_category=category,
        keyword=keyword)


@main_bp.route('/policies/<int:policy_id>')
def policy_detail(policy_id):
    """政策详情"""
    policy = Policy.query.get_or_404(policy_id)
    policy.view_count = (policy.view_count or 0) + 1
    if not policy.is_read:
        policy.is_read = True
    db.session.commit()
    return render_template('policy_detail.html', policy=policy)


@main_bp.route('/knowledge')
def knowledge_list():
    """知识库列表页"""
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category_id', 0, type=int)
    keyword = request.args.get('q', '')

    query = KnowledgeItem.query

    if category_id:
        query = query.filter_by(category_id=category_id)

    if keyword:
        query = query.filter(
            db.or_(
                KnowledgeItem.title.contains(keyword),
                KnowledgeItem.content.contains(keyword),
                KnowledgeItem.tags.contains(keyword)
            )
        )

    query = query.order_by(KnowledgeItem.is_pinned.desc(), KnowledgeItem.updated_at.desc())
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    categories = Category.query.order_by(Category.sort_order).all()

    return render_template('knowledge.html',
        items=pagination.items,
        pagination=pagination,
        categories=categories,
        current_category_id=category_id,
        keyword=keyword)


@main_bp.route('/knowledge/<int:item_id>')
def knowledge_detail(item_id):
    """知识库条目详情"""
    item = KnowledgeItem.query.get_or_404(item_id)
    item.view_count = (item.view_count or 0) + 1
    db.session.commit()
    return render_template('knowledge_detail.html', item=item)
