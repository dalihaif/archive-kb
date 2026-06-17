"""
前端展示路由
"""
from flask import Blueprint, render_template, request, jsonify
from models import db, Policy, Category, KnowledgeItem, MonitorSource, MonitorLog
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


def _main_fts_search_policies(keyword):
    """FTS5 全文搜索政策"""
    try:
        from sqlalchemy import text
        safe_kw = keyword.replace('"', '').replace("'", '')
        results = db.session.execute(
            text("SELECT rowid FROM policies_fts WHERE policies_fts MATCH :q LIMIT 500"),
            {"q": f'"{safe_kw}"'}
        ).fetchall()
        if results:
            return [r[0] for r in results]
    except Exception:
        pass
    return None


def _main_fts_search_knowledge(keyword):
    """FTS5 全文搜索知识库"""
    try:
        from sqlalchemy import text
        safe_kw = keyword.replace('"', '').replace("'", '')
        results = db.session.execute(
            text("SELECT rowid FROM knowledge_fts WHERE knowledge_fts MATCH :q LIMIT 500"),
            {"q": f'"{safe_kw}"'}
        ).fetchall()
        if results:
            return [r[0] for r in results]
    except Exception:
        pass
    return None


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
        fts_ids = _main_fts_search_policies(keyword)
        if fts_ids:
            query = query.filter(Policy.id.in_(fts_ids))
        else:
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


def _get_category_ids(cat_id):
    """获取父分类及所有子分类的ID列表"""
    cat_ids = [cat_id]
    for child in Category.query.filter_by(parent_id=cat_id).all():
        cat_ids.append(child.id)
    return cat_ids


def _get_category_total_count(cat):
    """获取分类的条目总数（包含子分类）"""
    if cat.children:
        cat_ids = [cat.id] + [c.id for c in cat.children]
        return KnowledgeItem.query.filter(KnowledgeItem.category_id.in_(cat_ids)).count()
    return cat.knowledge_items.count()


@main_bp.route('/knowledge')
def knowledge_list():
    """知识库列表页"""
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category_id', 0, type=int)
    keyword = request.args.get('q', '')

    query = KnowledgeItem.query

    if category_id:
        cat_ids = _get_category_ids(category_id)
        query = query.filter(KnowledgeItem.category_id.in_(cat_ids))

    if keyword:
        fts_ids = _main_fts_search_knowledge(keyword)
        if fts_ids:
            query = query.filter(KnowledgeItem.id.in_(fts_ids))
        else:
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
    total_all = KnowledgeItem.query.count()

    cat_counts = {}
    for c in categories:
        cat_counts[c.id] = _get_category_total_count(c)

    return render_template('knowledge.html',
        items=pagination.items,
        pagination=pagination,
        categories=categories,
        current_category_id=category_id,
        keyword=keyword,
        total_all=total_all,
        cat_counts=cat_counts)


@main_bp.route('/knowledge/<int:item_id>')
def knowledge_detail(item_id):
    """知识库条目详情"""
    item = KnowledgeItem.query.get_or_404(item_id)
    item.view_count = (item.view_count or 0) + 1
    db.session.commit()
    return render_template('knowledge_detail.html', item=item)
