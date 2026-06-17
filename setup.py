#!/usr/bin/env python3
"""
setup.py - 依赖安装脚本（由 start.bat 调用）
处理：Python 检测、便携版下载、pip 安装、依赖安装
"""
import os
import sys
import urllib.request
import zipfile
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 5050
PYPORTABLE_DIR = os.path.join(PROJECT_DIR, "pyportable")


def run(cmd, check=True, capture=False):
    """运行命令，返回 (returncode, stdout)"""
    print(f"  > {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    if check and result.returncode != 0:
        print(f"    失败 (code {result.returncode})")
        if result.stderr:
            print(f"    错误: {result.stderr[:200]}")
        sys.exit(1)
    return result.returncode, result.stdout


def find_python():
    """查找可用的 Python 解释器，返回路径或 None"""
    # 1. 便携版
    portable_exe = os.path.join(PYPORTABLE_DIR, "python.exe")
    if os.path.exists(portable_exe):
        print(f"[OK] 找到便携 Python: {portable_exe}")
        return portable_exe

    # 2. 系统 Python
    for cmd in ["python", "py -3", "python3"]:
        try:
            result = subprocess.run(
                f"{cmd} -c \"import sys; exit(0 if sys.version_info >= (3,10) else 1)\"",
                shell=True, capture_output=True
            )
            if result.returncode == 0:
                print(f"[OK] 找到系统 Python: {cmd}")
                return cmd
        except Exception:
            pass

    return None


def download_file(url, dest):
    """下载文件"""
    print(f"  下载: {url}")
    print(f"  保存到: {dest}")
    urllib.request.urlretrieve(url, dest)
    print(f"  下载完成 ({os.path.getsize(dest)} bytes)")


def install_portable_python():
    """下载并安装便携 Python"""
    print("=" * 60)
    print("未检测到 Python，正在自动安装运行环境...")
    print("=" * 60)

    ver = "3.12.10"
    zip_name = f"python-{ver}-embed-amd64.zip"
    zip_url = f"https://www.python.org/ftp/python/{ver}/{zip_name}"
    zip_path = os.path.join(PYPORTABLE_DIR, zip_name)

    os.makedirs(PYPORTABLE_DIR, exist_ok=True)

    # 下载
    print("\n[1/4] 正在下载 Python 便携版...")
    try:
        download_file(zip_url, zip_path)
    except Exception as e:
        print(f"[错误] 下载失败: {e}")
        print("  请检查网络连接，或手动下载后放入 pyportable/ 目录")
        sys.exit(1)

    # 解压
    print("\n[2/4] 正在解压 Python...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(PYPORTABLE_DIR)
        os.remove(zip_path)
        print("  解压完成!")
    except Exception as e:
        print(f"[错误] 解压失败: {e}")
        sys.exit(1)

    # 启用 site-packages
    print("\n[3/4] 配置 Python 环境...")
    for f in os.listdir(PYPORTABLE_DIR):
        if f.endswith("._pth"):
            pth_path = os.path.join(PYPORTABLE_DIR, f)
            with open(pth_path, 'r') as pf:
                content = pf.read()
            content = content.replace("#import site", "import site")
            with open(pth_path, 'w') as pf:
                pf.write(content)
            print(f"  已启用 site-packages: {f}")
            break

    # 安装 pip
    print("\n[4/4] 正在安装 pip...")
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = os.path.join(PYPORTABLE_DIR, "get-pip.py")
    try:
        download_file(get_pip_url, get_pip_path)
        subprocess.run(
            [os.path.join(PYPORTABLE_DIR, "python.exe"), get_pip_path, "--no-warn-script-location"],
            check=True
        )
        os.remove(get_pip_path)
        print("  pip 安装完成!")
    except Exception as e:
        print(f"[错误] pip 安装失败: {e}")
        sys.exit(1)

    print("\nPython 环境安装完成!")
    return os.path.join(PYPORTABLE_DIR, "python.exe")


def check_and_install_deps(python_exe):
    """检查并安装项目依赖"""
    print("\n正在检查项目依赖...")

    core_packages = [
        "flask", "flask-sqlalchemy", "beautifulsoup4",
        "lxml", "requests", "apscheduler", "openpyxl"
    ]

    # 检查核心依赖
    test_import = " ".join([f"import {p.replace('-', '_')}" for p in core_packages])
    test_import = test_import.replace("flask_sqlalchemy", "from flask_sqlalchemy import SQLAlchemy")
    test_import = test_import.replace("beautifulsoup4", "import bs4")
    test_import = test_import.replace("flask_sqlalchemy", "")
    # 简单检查：尝试导入每个包
    missing = []
    import_map = {
        "flask": "flask",
        "flask-sqlalchemy": "flask_sqlalchemy",
        "beautifulsoup4": "bs4",
        "lxml": "lxml",
        "requests": "requests",
        "apscheduler": "apscheduler",
        "openpyxl": "openpyxl",
    }
    for pkg, module in import_map.items():
        result = subprocess.run(
            f'"{python_exe}" -c "import {module}"',
            shell=True, capture_output=True
        )
        if result.returncode != 0:
            missing.append(pkg)

    if missing:
        print(f"  缺少依赖: {', '.join(missing)}")
        print("  正在安装核心依赖 (3~5 分钟，请耐心等待)...")
        req_file = os.path.join(PROJECT_DIR, "requirements.txt")
        if os.path.exists(req_file):
            subprocess.run(
                f'"{python_exe}" -m pip install -r "{req_file}"',
                shell=True, check=True
            )
        else:
            subprocess.run(
                f'"{python_exe}" -m pip install ' + " ".join(core_packages),
                shell=True, check=True
            )
        print("  核心依赖安装完成!")
    else:
        print("  核心依赖已满足。")

    # 可选依赖: scrapling
    result = subprocess.run(
        f'"{python_exe}" -c "import scrapling"',
        shell=True, capture_output=True
    )
    if result.returncode != 0:
        print("\n  正在安装 Scrapling (智能网页抓取引擎)...")
        result = subprocess.run(
            f'"{python_exe}" -m pip install scrapling',
            shell=True, capture_output=True
        )
        if result.returncode == 0:
            print("  Scrapling 安装完成!")
        else:
            print("  [提示] Scrapling 安装失败，将使用备用抓取引擎。")
    else:
        print("  Scrapling 已安装。")


def main():
    print("=" * 60)
    print("  档案政策监控与知识库平台 - 环境检查")
    print("=" * 60)

    # 检查项目文件
    if not os.path.exists(os.path.join(PROJECT_DIR, "app.py")):
        print("\n[错误] 未找到 app.py")
        print("  请确保 start.bat 位于 archive-kb 项目目录下。")
        input("\n按回车键退出...")
        sys.exit(1)

    # 查找 Python
    python_exe = find_python()
    if python_exe is None:
        python_exe = install_portable_python()

    # 安装依赖
    check_and_install_deps(python_exe)

    # 启动服务器
    print("\n" + "=" * 60)
    print("  启动服务器...")
    print("=" * 60)
    print(f"\n  本地访问:   http://127.0.0.1:{PORT}")
    print(f"  管理后台:   http://127.0.0.1:{PORT}/admin")
    print(f"\n  [提示] 后台无需登录，直接进入即可使用")
    print(f"  [提示] 关闭方式: 按 Ctrl+C 或直接关闭此窗口\n")
    print("=" * 60)
    print()

    # 3秒后自动打开浏览器
    import threading
    def open_browser():
        import time
        time.sleep(3)
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    threading.Thread(target=open_browser, daemon=True).start()

    # 启动 Flask
    os.chdir(PROJECT_DIR)
    subprocess.run(f'"{python_exe}" app.py', shell=True)


if __name__ == "__main__":
    main()
