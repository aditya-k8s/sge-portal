/*
 * Shared front-end behaviour: the install prompt, loading states, and
 * navigation progress. No dependencies -- Alpine.js handles the sidebar and
 * the dropdowns, and this file deliberately does not duplicate that.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'sge-install-dismissed';

  /* -- Install prompt ------------------------------------------------------ */

  var deferredPrompt = null;

  function isStandalone() {
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true
    );
  }

  function dismissedRecently() {
    try {
      var until = window.localStorage.getItem(STORAGE_KEY);
      return until && Date.now() < parseInt(until, 10);
    } catch (error) {
      // Private browsing can throw on localStorage access.
      return false;
    }
  }

  function rememberDismissal() {
    try {
      // Ask again in a fortnight rather than never.
      window.localStorage.setItem(
        STORAGE_KEY, String(Date.now() + 14 * 24 * 60 * 60 * 1000)
      );
    } catch (error) {
      /* Nothing to do: the banner simply reappears next visit. */
    }
  }

  function showInstallAffordances() {
    document.querySelectorAll('[data-install-trigger]').forEach(function (el) {
      el.hidden = false;
    });
    if (!dismissedRecently() && !document.getElementById('sge-install-banner')) {
      buildBanner();
    }
  }

  function hideInstallAffordances() {
    document.querySelectorAll('[data-install-trigger]').forEach(function (el) {
      el.hidden = true;
    });
    var banner = document.getElementById('sge-install-banner');
    if (banner) {
      banner.remove();
    }
  }

  function buildBanner() {
    var root = document.getElementById('sge-install-root');
    if (!root) {
      return;
    }
    var banner = document.createElement('div');
    banner.id = 'sge-install-banner';
    banner.setAttribute('role', 'region');
    banner.setAttribute('aria-label', 'Install this app');
    banner.innerHTML =
      '<img src="' + root.dataset.icon + '" alt="">' +
      '<div class="text">' +
      '<div class="title">Install ' + root.dataset.appName + '</div>' +
      '<div class="subtitle">Open it like an app, straight from your home screen.</div>' +
      '</div>' +
      '<button type="button" class="install-action" data-install-accept>Install</button>' +
      '<button type="button" class="dismiss" aria-label="Not now">&times;</button>';

    banner.querySelector('[data-install-accept]').addEventListener('click', promptInstall);
    banner.querySelector('.dismiss').addEventListener('click', function () {
      rememberDismissal();
      banner.remove();
    });
    root.appendChild(banner);
  }

  function promptInstall() {
    if (!deferredPrompt) {
      return;
    }
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(function (choice) {
      if (choice.outcome !== 'accepted') {
        rememberDismissal();
      }
      deferredPrompt = null;
      hideInstallAffordances();
    });
  }

  // Chrome fires this only when the app actually meets the install criteria:
  // served over HTTPS (or localhost), a valid manifest with 192px and 512px
  // icons, and a registered service worker with a fetch handler.
  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
    if (!isStandalone()) {
      showInstallAffordances();
    }
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    hideInstallAffordances();
  });

  document.addEventListener('click', function (event) {
    var trigger = event.target.closest('[data-install-trigger]');
    if (trigger) {
      event.preventDefault();
      promptInstall();
    }
  });

  /* -- Loading states ------------------------------------------------------ */

  // Disable the submit button and show a spinner, so a slow upload or PDF
  // build does not look like nothing happened -- and cannot be submitted
  // twice by an impatient second click.
  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (form.dataset.noLoading !== undefined) {
      return;
    }
    var button = form.querySelector('button[type="submit"], input[type="submit"]');
    if (!button || button.disabled) {
      return;
    }
    // Let the browser's own validation run first.
    if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
      return;
    }
    window.setTimeout(function () {
      button.classList.add('is-loading');
      button.disabled = true;
      var label = button.dataset.loadingLabel;
      if (label) {
        button.setAttribute('aria-label', label);
      }
    }, 0);
  });

  /* -- Navigation progress ------------------------------------------------- */

  function startProgress() {
    var bar = document.getElementById('sge-progress');
    if (!bar) {
      return;
    }
    bar.style.opacity = '1';
    bar.style.width = '35%';
    window.setTimeout(function () { bar.style.width = '75%'; }, 250);
  }

  document.addEventListener('click', function (event) {
    var link = event.target.closest('a[href]');
    if (!link || link.target === '_blank' || link.hasAttribute('download')) {
      return;
    }
    var href = link.getAttribute('href');
    if (!href || href.charAt(0) === '#' || href.indexOf('javascript:') === 0) {
      return;
    }
    if (link.origin && link.origin !== window.location.origin) {
      return;
    }
    startProgress();
  });

  window.addEventListener('pageshow', function () {
    var bar = document.getElementById('sge-progress');
    if (bar) {
      bar.style.width = '100%';
      window.setTimeout(function () {
        bar.style.opacity = '0';
        bar.style.width = '0';
      }, 200);
    }
  });

  /* -- Offline awareness --------------------------------------------------- */

  function renderConnectionState() {
    var notice = document.getElementById('sge-offline-notice');
    if (notice) {
      notice.hidden = window.navigator.onLine;
    }
  }

  window.addEventListener('online', renderConnectionState);
  window.addEventListener('offline', renderConnectionState);
  document.addEventListener('DOMContentLoaded', renderConnectionState);
})();
