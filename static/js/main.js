/**
 * 档案政策监控与知识库 - 前端交互
 */
(function() {
    'use strict';

    // Toast 提示
    window.showToast = function(msg, type) {
        type = type || 'info';
        var toast = document.createElement('div');
        toast.className = 'toast align-items-center text-bg-' + type + ' border-0 position-fixed top-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.style.zIndex = '9999';
        toast.innerHTML = '<div class="d-flex"><div class="toast-body">' + msg + '</div><button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button></div>';
        document.body.appendChild(toast);
        var bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();
        toast.addEventListener('hidden.bs.toast', function() { toast.remove(); });
    };

    // 更新统计数据(如果有统计元素)
    var statRefresh = document.getElementById('statRefresh');
    if (statRefresh) {
        setInterval(function() {
            fetch('/admin/api/stats')
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    var todayEl = document.getElementById('statToday');
                    if (todayEl) todayEl.textContent = d.today_policies;
                })
                .catch(function() {});
        }, 60000);
    }

    // 搜索框防抖
    var searchTimer;
    var searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(function() {
                searchInput.form && searchInput.form.submit();
            }, 800);
        });
    }

    // 回到顶部
    var backTop = document.createElement('button');
    backTop.innerHTML = '<i class="bi bi-chevron-up"></i>';
    backTop.className = 'btn btn-sm position-fixed bottom-0 end-0 m-3 rounded-circle shadow';
    backTop.style.cssText = 'background-color: #1A2A4A; color: white; width: 36px; height: 36px; z-index: 999; opacity: 0; transition: opacity 0.3s;';
    backTop.onclick = function() { window.scrollTo({top: 0, behavior: 'smooth'}); };
    document.body.appendChild(backTop);

    window.addEventListener('scroll', function() {
        backTop.style.opacity = window.scrollY > 300 ? '1' : '0';
    });
})();
