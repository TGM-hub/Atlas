// tgm-core.js : cœur commun de l'Atlas et des trainers (pays, tiers, liens, stats).
// Généré par build.py (Atlas) depuis countries.json : ne pas modifier à la main.
// Les copies dans les repos des trainers sont rafraîchies par build.py quand elles existent.
// Script classique (pas de module) : marche en file:// comme sur GitHub Pages.
(function (root) {
  'use strict';
  var VERSION = '/*VERSION*/';
  var C = /*COUNTRIES*/;
  var CONTINENTS = { EU: { fr: 'Europe', en: 'Europe' }, AS: { fr: 'Asie', en: 'Asia' }, AF: { fr: 'Afrique', en: 'Africa' },
    NA: { fr: 'Amérique du Nord', en: 'North America' }, SA: { fr: 'Amérique du Sud', en: 'South America' }, OC: { fr: 'Océanie', en: 'Oceania' } };
  var TIER_NAMES = { 1: { fr: 'Courant', en: 'Common' }, 2: { fr: 'Régulier', en: 'Regular' }, 3: { fr: 'Rare', en: 'Rare' }, 4: { fr: 'Très rare', en: 'Very rare' } };

  function lsGet(k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function up(iso) { return String(iso || '').toUpperCase(); }
  function num(v) { return typeof v === 'number' && isFinite(v) ? v : null; }

  var intl = {};
  function intlName(iso, lang) {
    try { intl[lang] = intl[lang] || new Intl.DisplayNames([lang], { type: 'region' }); return intl[lang].of(iso); } catch (e) { return iso; }
  }

  // ---------------------------------------------------------------- pays
  function country(iso) { return C[up(iso)] || null; }
  function tierDefault(iso) { var c = country(iso); return c ? c.tier : 4; }
  // Les réglages de tier faits dans City Placer (cp.prefs.tierOv) s'appliquent partout
  function tier(iso) {
    var ov = (lsGet('cp.prefs', {}) || {}).tierOv || {};
    var t = +ov[up(iso)];
    return t >= 1 && t <= 4 ? t : tierDefault(iso);
  }
  function name(iso, lang) {
    lang = lang || 'fr';
    var c = country(iso);
    return (c && (c[lang] || c.en)) || intlName(up(iso), lang);
  }
  function flag(iso) {
    iso = up(iso);
    return /^[A-Z]{2}$/.test(iso) ? String.fromCodePoint(0x1F1A5 + iso.charCodeAt(0), 0x1F1A5 + iso.charCodeAt(1)) : '';
  }
  function plonkitUrl(iso) { var c = country(iso); return c && c.plonkit ? 'https://www.plonkit.net/' + c.plonkit : null; }
  // Google Maps avec le calque de couverture Street View
  function svUrl(iso) { var c = country(iso), s = c && c.sv; return s ? 'https://www.google.com/maps/@' + s[0] + ',' + s[1] + ',' + s[2] + 'z/data=!5m1!1e5' : null; }
  function topoUrl(iso) { var c = country(iso), s = c && c.sv; return s ? 'https://opentopomap.org/#map=' + s[2] + '/' + s[0] + '/' + s[1] : null; }
  function isos(filter) {
    var all = Object.keys(C);
    return typeof filter === 'function' ? all.filter(function (k) { return filter(C[k], k); }) : all;
  }

  // ---------------------------------------------------------------- stats communes
  // localStorage tgm.stats.<app> = { app, v, updatedAt, seen, correct, total, practiced, mastered, weak, due, byCountry }
  //   seen / correct : réponses données / justes (toutes sessions)
  //   total : éléments à apprendre ; practiced : déjà vus ; mastered : acquis ; weak : dernière réponse fausse ;
  //   due : à revoir (null si le trainer n'a pas de répétition espacée)
  //   byCountry : { ISO: { seen, correct, total?, practiced?, mastered?, weak? } }
  // Chaque trainer garde ses propres clés : ce résumé est un instantané qu'il réécrit après chaque réponse.
  var FIELDS = ['seen', 'correct', 'total', 'practiced', 'mastered', 'weak', 'due'];
  var PREFIX = 'tgm.stats.';
  function clean(o) {
    var r = {};
    FIELDS.forEach(function (f) { r[f] = num(o && o[f]); });
    return r;
  }
  var stats = {
    key: function (app) { return PREFIX + app; },
    read: function (app) { return lsGet(PREFIX + app, null); },
    write: function (app, s) {
      var out = clean(s);
      out.app = app; out.v = 1; out.updatedAt = new Date().toISOString();
      out.byCountry = {};
      var bc = (s && s.byCountry) || {};
      Object.keys(bc).forEach(function (k) {
        var iso = up(k), x = clean(bc[k]), y = {};
        if (!/^[A-Z]{2}$/.test(iso)) return;
        FIELDS.forEach(function (f) { if (x[f] != null) y[f] = x[f]; });
        out.byCountry[iso] = y;
      });
      return lsSet(PREFIX + app, out) ? out : null;
    },
    all: function () {
      var r = {};
      try {
        for (var i = 0; i < localStorage.length; i++) {
          var k = localStorage.key(i);
          if (k && k.indexOf(PREFIX) === 0) { var v = lsGet(k, null); if (v) r[k.slice(PREFIX.length)] = v; }
        }
      } catch (e) {}
      return r;
    },
    // Résume un historique Leitner {clé: [vus, justes, boîte, ...]} ; isoOf(clé) donne le pays (ou null)
    fromLeitner: function (hist, isoOf, opts) {
      opts = opts || {};
      var mastBox = opts.masteredBox || 4, s = { seen: 0, correct: 0, practiced: 0, mastered: 0, weak: 0, byCountry: {} };
      Object.keys(hist || {}).forEach(function (k) {
        var h = hist[k];
        if (!Array.isArray(h) || !h[0]) return;
        var iso = isoOf ? isoOf(k) : null, c = null;
        if (iso) c = s.byCountry[iso] = s.byCountry[iso] || { seen: 0, correct: 0, practiced: 0, mastered: 0, weak: 0 };
        var m = (h[2] || 0) >= mastBox ? 1 : 0, w = (h[2] || 0) === 0 ? 1 : 0;
        [s, c].forEach(function (o) { if (!o) return; o.seen += h[0]; o.correct += h[1] || 0; o.practiced++; o.mastered += m; o.weak += w; });
      });
      return s;
    },
  };

  root.TGM = {
    version: VERSION, countries: C, continents: CONTINENTS, tierNames: TIER_NAMES,
    country: country, has: function (iso) { return !!country(iso); }, isos: isos,
    tier: tier, tierDefault: tierDefault, name: name, flag: flag, continent: function (iso) { var c = country(iso); return c ? c.continent : null; },
    plonkitUrl: plonkitUrl, svUrl: svUrl, topoUrl: topoUrl,
    stats: stats,
  };
})(typeof window !== 'undefined' ? window : this);
