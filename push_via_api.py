#!/usr/bin/env python3
"""
通过 GitHub REST API 推送文件到仓库
解决 Git 推送被网络阻断的问题
"""
import base64
import json
import os
import sys

import requests

# ========== 配置区 ==========
REPO_OWNER = "dalihaif"
REPO_NAME = "archive-kb"
BRANCH = "main"
# 从环境变量读取 Token，或在这里直接填写
TOKEN = os.environ.get("GITHUB_TOKEN", "")
# ========== 配置区结束 ==========

if not TOKEN:
    print("ERROR: 请设置环境变量 GITHUB_TOKEN")
    print("  或直接在脚本中填写 TOKEN")
    sys.exit(1)

API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "archive-kb-pusher",
}

# 需要推送的文件列表（相对于项目根目录）
FILES_TO_PUSH = [
    "README.md",
    "app.py",
    "models.py",
    "crawler.py",
    "requirements.txt",
    "routes/admin.py",
    "routes/main.py",
    "routes/__init__.py",
    "templates/base.html",
    "templates/index.html",
    "templates/knowledge.html",
    "templates/policy_detail.html",
    "templates/admin/dashboard.html",
    "templates/admin/sources.html",
    "templates/admin/policies.html",
    "templates/admin/knowledge.html",
    "templates/admin/categories.html",
    "templates/admin/login.html",
]


def get_current_commit_sha():
    """获取当前分支最新 commit SHA"""
    url = f"{API_BASE}/branches/{BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()["commit"]["sha"]


def get_current_tree_sha(commit_sha):
    """获取当前 commit 的 tree SHA"""
    url = f"{API_BASE}/git/commits/{commit_sha}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()["tree"]["sha"]


def create_blob(content_bytes):
    """创建 blob，返回 SHA"""
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
    url = f"{API_BASE}/git/blobs"
    data = {"encoding": "base64", "content": content_b64}
    resp = requests.post(url, headers=HEADERS, json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["sha"]


def create_tree(base_tree_sha, file_list):
    """创建新 tree，返回 SHA"""
    tree_items = []
    for filepath in file_list:
        if not os.path.exists(filepath):
            print(f"  SKIP (not found): {filepath}")
            continue
        with open(filepath, "rb") as f:
            content_bytes = f.read()
        blob_sha = create_blob(content_bytes)
        tree_items.append({
            "path": filepath.replace("\\", "/"),
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        })
        print(f"  blob created: {filepath} ({len(content_bytes)} bytes)")

    url = f"{API_BASE}/git/trees"
    data = {"base_tree": base_tree_sha, "tree": tree_items}
    resp = requests.post(url, headers=HEADERS, json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["sha"]


def create_commit(tree_sha, parent_sha, message):
    """创建 commit，返回 SHA"""
    url = f"{API_BASE}/git/commits"
    data = {
        "message": message,
        "tree": tree_sha,
        "parents": [parent_sha],
    }
    resp = requests.post(url, headers=HEADERS, json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["sha"]


def update_branch(commit_sha):
    """更新分支引用到新 commit"""
    url = f"{API_BASE}/git/refs/heads/{BRANCH}"
    data = {"sha": commit_sha, "force": False}
    resp = requests.patch(url, headers=HEADERS, json=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def main():
    print(f"推送到: {REPO_OWNER}/{REPO_NAME} ({BRANCH})")
    print(f"文件数: {len(FILES_TO_PUSH)}")
    print("-" * 50)

    # 1. 获取当前状态
    print("获取当前分支信息...")
    commit_sha = get_current_commit_sha()
    tree_sha = get_current_tree_sha(commit_sha)
    print(f"  当前 commit: {commit_sha[:8]}")
    print(f"  当前 tree:   {tree_sha[:8]}")

    # 2. 创建 blobs 和新 tree
    print("\n创建 blobs 和新 tree...")
    new_tree_sha = create_tree(tree_sha, FILES_TO_PUSH)
    print(f"  新 tree: {new_tree_sha[:8]}")

    # 3. 创建 commit
    print("\n创建 commit...")
    message = "feat: 完整功能更新 - 全文抓取/FTS5搜索/Excel导出/关键词订阅/数据备份恢复/移除登录限制"
    new_commit_sha = create_commit(new_tree_sha, commit_sha, message)
    print(f"  新 commit: {new_commit_sha[:8]}")

    # 4. 更新分支
    print("\n更新分支引用...")
    result = update_branch(new_commit_sha)
    print(f"  成功! ref: {result['ref']}")
    print(f"  查看: https://github.com/{REPO_OWNER}/{REPO_NAME}/tree/{BRANCH}")


if __name__ == "__main__":
    main()
