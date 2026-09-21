/*
 * Public website behaviour: scroll reveal, counters, and the nav's scrolled
 * state. Loaded only by templates/website/base_public.html.
 *
 * Everything here is an enhancement. With JavaScript unavailable the page is
 * fully readable: the reveal styles are scoped to the .js-reveal class this
 * file adds, counters print their final value in the markup, and the nav is
 * legible without its scrolled state.
 */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

  /* -- Scroll reveal ------------------------------------------------------ */

  function initReveal() {
    // .wipe shares the same release mechanism, with a clip-path transition
    // instead of a fade.
    var targets = document.querySelectorAll('.reveal, .wipe');
    if (!targets.length) return;

    // Someone who asked for reduced motion, or an old browser with no
    // IntersectionObserver, simply gets the content with no animation.
    if (reduceMotion || !('IntersectionObserver' in window)) return;

    document.documentElement.classList.add('js-reveal');

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        // Stagger by position within the parent, so a row of cards resolves
        // left to right instead of all at once.
        var delay = Number(entry.target.dataset.revealDelay || 0);
        setTimeout(function () {
          entry.target.classList.add('is-visible');
        }, delay);
        observer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.1 });

    targets.forEach(function (target) {
      observer.observe(target);
    });
  }

  /* -- Counters -----------------------------------------------------------
   * Counts up to the number already written in the element, so the final
   * value is in the HTML and survives with no JavaScript.
   */

  function initCounters() {
    var counters = document.querySelectorAll('[data-count-to]');
    if (!counters.length || reduceMotion || !('IntersectionObserver' in window)) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        animate(entry.target);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.5 });

    counters.forEach(function (counter) {
      observer.observe(counter);
    });
  }

  function animate(element) {
    var target = parseFloat(element.dataset.countTo);
    if (isNaN(target)) return;

    var decimals = (element.dataset.countTo.split('.')[1] || '').length;
    var suffix = element.dataset.countSuffix || '';
    var prefix = element.dataset.countPrefix || '';
    var duration = 1400;
    var started = null;

    function step(timestamp) {
      if (started === null) started = timestamp;
      var elapsed = timestamp - started;
      var progress = Math.min(elapsed / duration, 1);
      // Ease out, so it decelerates into the final figure.
      var eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = prefix + (target * eased).toFixed(decimals) + suffix;
      if (progress < 1) window.requestAnimationFrame(step);
    }

    window.requestAnimationFrame(step);
  }

  /* -- Nav scrolled state -------------------------------------------------- */

  function initNav() {
    var nav = document.querySelector('[data-site-nav]');
    if (!nav) return;

    function update() {
      nav.classList.toggle('is-scrolled', window.scrollY > 12);
    }

    update();
    window.addEventListener('scroll', update, { passive: true });
  }

  /* -- Cursor spotlight ---------------------------------------------------
   * Writes the pointer position onto the section as percentages, which the
   * .spotlight gradient reads. Pointer events only, so a touch device simply
   * keeps the default position.
   */

  function initSpotlight() {
    var sections = document.querySelectorAll('.spotlight');
    if (!sections.length || reduceMotion) return;

    Array.prototype.forEach.call(sections, function (section) {
      var pending = false;
      var lastEvent = null;

      section.addEventListener('pointermove', function (event) {
        lastEvent = event;
        if (pending) return;
        pending = true;
        // Batched into a frame: pointermove fires far faster than the screen
        // refreshes, and writing a custom property forces style recalculation.
        window.requestAnimationFrame(function () {
          pending = false;
          var box = section.getBoundingClientRect();
          section.style.setProperty('--mx', ((lastEvent.clientX - box.left) / box.width * 100) + '%');
          section.style.setProperty('--my', ((lastEvent.clientY - box.top) / box.height * 100) + '%');
        });
      });
    });
  }

  /* -- Card tilt ----------------------------------------------------------- */

  function initTilt() {
    var cards = document.querySelectorAll('[data-tilt]');
    if (!cards.length || reduceMotion) return;

    // A tilt that follows a finger is unpleasant, and the hover state it
    // implies does not exist on touch.
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    var MAX = 6; // degrees; beyond this the text starts to distort

    Array.prototype.forEach.call(cards, function (card) {
      var pending = false;
      var lastEvent = null;

      card.addEventListener('pointermove', function (event) {
        lastEvent = event;
        if (pending) return;
        pending = true;
        window.requestAnimationFrame(function () {
          pending = false;
          var box = card.getBoundingClientRect();
          var px = (lastEvent.clientX - box.left) / box.width - 0.5;
          var py = (lastEvent.clientY - box.top) / box.height - 0.5;
          card.classList.add('is-tilting');
          card.style.setProperty('--ry', (px * MAX * 2).toFixed(2) + 'deg');
          card.style.setProperty('--rx', (-py * MAX * 2).toFixed(2) + 'deg');
        });
      });

      card.addEventListener('pointerleave', function () {
        card.classList.remove('is-tilting');
        card.style.setProperty('--rx', '0deg');
        card.style.setProperty('--ry', '0deg');
      });
    });
  }

  /* -- Plotter -------------------------------------------------------------
   * Measures each stroke so the dash animation covers exactly its own length,
   * then releases the figure when it scrolls into view.
   */

  function initPlotter() {
    var figures = document.querySelectorAll('.plot');
    if (!figures.length) return;

    Array.prototype.forEach.call(figures, function (figure) {
      var strokes = figure.querySelectorAll('[data-draw]');

      Array.prototype.forEach.call(strokes, function (stroke) {
        var length = 0;
        try {
          length = stroke.getTotalLength ? stroke.getTotalLength() : 0;
        } catch (error) {
          length = 0; // getTotalLength throws on some shapes in older engines
        }
        if (!length) length = 600;
        stroke.style.setProperty('--len', Math.ceil(length));
      });

      if (reduceMotion || !('IntersectionObserver' in window)) {
        // Show the finished drawing rather than an empty frame.
        figure.classList.add('is-drawing');
        return;
      }

      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-drawing');
          observer.unobserve(entry.target);
        });
      }, { threshold: 0.25 });

      observer.observe(figure);
    });
  }

  /* -- Scan travel distance ------------------------------------------------
   * The scanning line animates by transform, which needs the section height
   * in pixels; a percentage would translate by its own 2px height.
   */

  function initScanlines() {
    var lines = document.querySelectorAll('.scanline');
    if (!lines.length) return;

    function measure() {
      Array.prototype.forEach.call(lines, function (line) {
        var host = line.parentElement;
        if (host) line.style.setProperty('--scan-height', host.offsetHeight + 'px');
      });
    }

    measure();
    window.addEventListener('resize', measure, { passive: true });
  }

  /* -- Scroll progress ------------------------------------------------------ */

  function initProgress() {
    var bar = document.querySelector('.scroll-progress');
    if (!bar) return;

    var pending = false;

    function update() {
      pending = false;
      var scrollable = document.documentElement.scrollHeight - window.innerHeight;
      var progress = scrollable > 0 ? window.scrollY / scrollable : 0;
      bar.style.setProperty('--progress', Math.min(Math.max(progress, 0), 1).toFixed(4));
    }

    window.addEventListener('scroll', function () {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(update);
    }, { passive: true });

    update();
  }

  function init() {
    initReveal();
    initCounters();
    initNav();
    initSpotlight();
    initTilt();
    initPlotter();
    initScanlines();
    initProgress();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
