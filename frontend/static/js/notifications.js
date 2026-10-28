/**
 * Gestion des notifications
 * - Polling toutes les 30 secondes
 * - Badge compteur dans la navbar
 * - Dropdown avec les dernières notifications
 * - Toasts Bootstrap pour les nouvelles notifications
 * - Notifications desktop (Browser Notification API)
 */

(function() {
    'use strict';

    var _lastUnreadCount = -1;
    var _notificationPermissionRequested = false;
    var POLL_INTERVAL = 30 * 1000; // 30 secondes

    function getCSRFToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }

    // ========== Badge compteur ==========

    function updateBadge(count) {
        var badge = document.getElementById('notification-badge');
        if (!badge) return;
        badge.textContent = count > 99 ? '99+' : count;
        if (count > 0) {
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }

    // ========== Toast Bootstrap ==========

    function showToast(title, message) {
        // Créer le conteneur de toasts s'il n'existe pas
        var container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = 'position:fixed;top:1rem;right:1rem;z-index:9999;display:flex;flex-direction:column;gap:0.5rem;';
            document.body.appendChild(container);
        }

        var toast = document.createElement('div');
        toast.className = 'bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg shadow-lg p-4 max-w-sm transform transition-all duration-300 translate-x-full opacity-0';
        toast.innerHTML =
            '<div class="flex items-start">' +
                '<div class="flex-shrink-0 text-blue-500"><i class="fas fa-bell"></i></div>' +
                '<div class="ml-3 flex-1">' +
                    '<p class="text-sm font-medium text-gray-900 dark:text-gray-100">' + escapeHtml(title) + '</p>' +
                    '<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">' + escapeHtml(message) + '</p>' +
                '</div>' +
                '<button class="ml-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" onclick="this.closest(\'div[class*=bg-white]\').remove()">' +
                    '<i class="fas fa-times"></i>' +
                '</button>' +
            '</div>';

        container.appendChild(toast);

        // Animer l'entrée
        requestAnimationFrame(function() {
            toast.classList.remove('translate-x-full', 'opacity-0');
        });

        // Supprimer après 5 secondes
        setTimeout(function() {
            toast.classList.add('translate-x-full', 'opacity-0');
            setTimeout(function() { toast.remove(); }, 300);
        }, 5000);
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ========== Notifications desktop ==========

    function requestNotificationPermission() {
        if (_notificationPermissionRequested) return;
        if (!('Notification' in window)) return;
        if (Notification.permission === 'default') {
            _notificationPermissionRequested = true;
            Notification.requestPermission();
        }
    }

    function sendDesktopNotification(title, body) {
        if (!('Notification' in window)) return;
        if (Notification.permission !== 'granted') return;
        if (document.hasFocus()) return;

        try {
            new Notification(title, {
                body: body,
                icon: '/static/img/favicon.ico'
            });
        } catch (e) {
            // Silently ignore if notifications fail
        }
    }

    // ========== Dropdown notifications ==========

    function renderNotificationItem(notif) {
        var isRead = notif.is_read;
        var timeAgo = formatTimeAgo(notif.created_at);
        var typeIcon = getNotifIcon(notif.type);

        return '<div class="px-4 py-3 border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer ' +
            (!isRead ? 'bg-blue-50 dark:bg-blue-900/20' : '') + '" ' +
            'onclick="window._markNotifRead(' + notif.id + ', this)">' +
            '<div class="flex items-start">' +
                '<div class="flex-shrink-0 text-gray-400 mt-0.5"><i class="fas ' + typeIcon + '"></i></div>' +
                '<div class="ml-3 flex-1 min-w-0">' +
                    '<p class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">' + escapeHtml(notif.title) + '</p>' +
                    '<p class="text-xs text-gray-500 dark:text-gray-400 truncate">' + escapeHtml(notif.message || '') + '</p>' +
                    '<p class="text-xs text-gray-400 dark:text-gray-500 mt-1">' + timeAgo + '</p>' +
                '</div>' +
                (!isRead ? '<div class="flex-shrink-0 ml-2"><span class="h-2 w-2 bg-blue-500 rounded-full inline-block"></span></div>' : '') +
            '</div>' +
        '</div>';
    }

    function getNotifIcon(type) {
        switch (type) {
            case 'warning': return 'fa-exclamation-triangle text-yellow-500';
            case 'error': return 'fa-exclamation-circle text-red-500';
            case 'success': return 'fa-check-circle text-green-500';
            default: return 'fa-info-circle text-blue-500';
        }
    }

    function formatTimeAgo(isoString) {
        if (!isoString) return '';
        var now = new Date();
        var date = new Date(isoString);
        var diffMs = now - date;
        var diffMin = Math.floor(diffMs / 60000);
        if (diffMin < 1) return "A l'instant";
        if (diffMin < 60) return 'Il y a ' + diffMin + ' min';
        var diffH = Math.floor(diffMin / 60);
        if (diffH < 24) return 'Il y a ' + diffH + 'h';
        var diffD = Math.floor(diffH / 24);
        if (diffD < 7) return 'Il y a ' + diffD + 'j';
        return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
    }

    function loadNotificationsDropdown() {
        var listEl = document.getElementById('notification-list');
        if (!listEl) return;

        fetch('/api/v1/notifications?limit=5')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.status === 'success' && data.notifications && data.notifications.length > 0) {
                    listEl.innerHTML = data.notifications.map(renderNotificationItem).join('');
                } else {
                    listEl.innerHTML = '<div class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center">Aucune notification</div>';
                }
            })
            .catch(function() {
                listEl.innerHTML = '<div class="px-4 py-3 text-sm text-red-500 text-center">Erreur de chargement</div>';
            });
    }

    // ========== Polling ==========

    function updateUnreadCount() {
        fetch('/api/v1/notifications/unread-count')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.status !== 'success') return;
                var count = data.unread_count || 0;
                updateBadge(count);

                // Détecter les nouvelles notifications
                if (_lastUnreadCount >= 0 && count > _lastUnreadCount) {
                    var diff = count - _lastUnreadCount;
                    showToast('Nouvelle notification', 'Vous avez ' + diff + ' nouvelle(s) notification(s)');
                    sendDesktopNotification('GestionBudget', 'Vous avez ' + diff + ' nouvelle(s) notification(s)');
                    loadNotificationsDropdown();
                }

                _lastUnreadCount = count;
            })
            .catch(function(error) {
                console.error('Erreur polling notifications:', error);
            });
    }

    // ========== Actions ==========

    window._markNotifRead = function(notificationId, el) {
        fetch('/api/v1/notifications/mark-as-read/' + notificationId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success && el) {
                el.classList.remove('bg-blue-50', 'dark:bg-blue-900/20');
                var dot = el.querySelector('.bg-blue-500.rounded-full');
                if (dot) dot.remove();
            }
            updateUnreadCount();
        })
        .catch(function(error) {
            console.error('Erreur marquage notification:', error);
        });
    };

    function markAllAsRead() {
        fetch('/api/v1/notifications/mark-all-read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                updateUnreadCount();
                loadNotificationsDropdown();
            }
        })
        .catch(function(error) {
            console.error('Erreur marquage toutes notifications:', error);
        });
    }

    // ========== Initialisation ==========

    function init() {
        // Polling
        updateUnreadCount();
        setInterval(updateUnreadCount, POLL_INTERVAL);

        // Toggle dropdown
        var bellBtn = document.getElementById('notification-bell');
        var dropdown = document.getElementById('notification-dropdown');

        if (bellBtn && dropdown) {
            bellBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                var isHidden = dropdown.classList.contains('hidden');
                dropdown.classList.toggle('hidden');
                bellBtn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
                if (isHidden) {
                    loadNotificationsDropdown();
                    requestNotificationPermission();
                }
            });

            // Fermer en cliquant ailleurs
            document.addEventListener('click', function(e) {
                if (!dropdown.contains(e.target) && e.target !== bellBtn) {
                    dropdown.classList.add('hidden');
                    bellBtn.setAttribute('aria-expanded', 'false');
                }
            });
        }

        // Mark all as read button
        var markAllBtn = document.getElementById('mark-all-read-btn');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                markAllAsRead();
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
