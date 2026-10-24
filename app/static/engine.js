/* AlayakAlert: движок правил в браузере.
   Порт engine/*.py. Регулярные выражения приходят из Python (ENGINE_DATA, см. app/export_engine.py)
   и переводятся в синтаксис JavaScript функцией py(). Совпадение с Python проверяет
   python -m evaluation.js_parity. Работает без сервера и без интернета: текст никуда не отправляется. */
(function (root) {
  "use strict";
  var E = root.ENGINE_DATA;
  var WC = "\\p{L}\\p{N}_";
  var BOUND = "(?:(?<=[" + WC + "])(?![" + WC + "])|(?<![" + WC + "])(?=[" + WC + "]))";

  // Python re -> JS RegExp (флаг u): \w, \W, \b — по Unicode, как в Python; (?P<name> -> (?<name>; $ как в Python
  function conv(src) {
    src = src.split("[^\\W\\d_]").join("[\\p{L}]");
    var out = "", cls = false;
    for (var i = 0; i < src.length; i++) {
      var c = src[i];
      if (c === "\\") {
        var n = src[i + 1];
        if (n === "w") out += cls ? WC : "[" + WC + "]";
        else if (n === "W") { if (cls) throw new Error("\\W в классе: " + src); out += "[^" + WC + "]"; }
        else if (n === "b") out += cls ? "\\b" : BOUND;
        else if (n === "-" && !cls) out += "-";
        else out += c + n;
        i++; continue;
      }
      if (cls) { if (c === "]") cls = false; out += c; continue; }
      if (c === "[") {
        cls = true; out += c;
        if (src[i + 1] === "^") { out += "^"; i++; }
        if (src[i + 1] === "]") { out += "\\]"; i++; }
        continue;
      }
      if (c === "(" && src.substr(i, 4) === "(?P<") { out += "(?<"; i += 3; continue; }
      if (c === "$") { out += "(?=\\n?$)"; continue; }
      out += c;
    }
    return out;
  }
  var cache = {};
  function py(src, flags) {
    var key = src + "\u0000" + (flags || "");
    if (!cache[key]) cache[key] = new RegExp(conv(src), "u" + (flags || ""));
    return cache[key];
  }
  function gl(rx) { return new RegExp(rx.source, rx.flags.indexOf("g") >= 0 ? rx.flags : rx.flags + "g"); }
  function sticky(rx) { return new RegExp(rx.source, rx.flags.replace("g", "") + "y"); }
  // re.search(text, pos) / re.match / re.finditer
  function search(rx, text, pos) {
    if (!pos) return rx.exec(text);
    var g = gl(rx); g.lastIndex = pos; return g.exec(text);
  }
  function match(rx, text) { var y = sticky(rx); y.lastIndex = 0; return y.exec(text); }
  function finditer(rx, text, pos) {
    var g = gl(rx), out = [], m;
    g.lastIndex = pos || 0;
    while ((m = g.exec(text)) !== null) { out.push(m); if (m[0] === "") g.lastIndex++; }
    return out;
  }
  function end(m) { return m.index + m[0].length; }
  function has(rx, text) { return rx.exec(text) !== null; }

  function load(group) { var o = {}; Object.keys(E.rx[group]).forEach(function (k) { o[k] = py(E.rx[group][k][0], E.rx[group][k][1]); }); return o; }
  var N = load("N"), R = load("R"), C = load("C"), S = load("S"), T = load("T"), I = load("I");

  function splitWs(s) { return s.split(/\s+/u).filter(Boolean); }
  function chars(s) { return Array.from(s); }
  function isAlpha(c) { return /^\p{L}$/u.test(c); }
  function isDigit(c) { return /^\p{Nd}$/u.test(c); }
  function trim(s, n) {
    n = n || 180; s = splitWs(s).join(" ");
    var a = chars(s);
    return a.length <= n ? s : a.slice(0, n - 1).join("") + "…";
  }
  function pyRound(x) { var r = Math.round(x); if (Math.abs(x % 1) === 0.5 && r % 2 !== 0) r -= 1; return r; }
  function splitlines(s) { return (s || "").split(new RegExp("\\r\\n|[\\n\\r\\v\\f\\x1c\\x1d\\x1e\\x85\\u2028\\u2029]")); }
  function pyStrip(s) { return s.replace(/^\s+|\s+$/gu, ""); }

  /* ── normalize.py ─────────────────────────────────────── */
  function translitWord(w) {
    var out = w;
    E.translit_digraphs.forEach(function (p) { out = out.split(p[0]).join(p[1]); });
    return chars(out).map(function (c) { return Object.prototype.hasOwnProperty.call(E.translit, c) ? E.translit[c] : c; }).join("");
  }
  function leetOk(a, i) {
    var c = a[i], l = i > 0 ? a[i - 1] : "", r = i + 1 < a.length ? a[i + 1] : "";
    if (c === "!") return isAlpha(l) && isAlpha(r);
    if (isDigit(c)) return isAlpha(l);
    return isAlpha(l) || isAlpha(r);
  }
  function hasKey(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function fixToken(tok) {
    if (has(N.URLISH_RE, tok)) return [tok, tok];
    var cyr = has(N.CYR_RE, tok), lat = has(N.LAT_RE, tok), a = chars(tok);
    if (cyr) {
      return [a.map(function (c, i) { return hasKey(E.lookalike, c) ? E.lookalike[c] : (hasKey(E.leet, c) && leetOk(a, i) ? E.leet[c] : c); }).join(""), tok];
    }
    if (lat) {
      var l = a.map(function (c, i) { return hasKey(E.lat_leet, c) && leetOk(a, i) ? E.lat_leet[c] : c; }).join("");
      if (l.replace(/[^a-z]/g, "").length >= 3) return [translitWord(l), l];
      return [tok, tok];
    }
    return [tok, tok];
  }
  function clean(text) {
    var t = (text || "").normalize("NFKC");
    t = t.replace(gl(N.ZERO_WIDTH), "");
    E.emoji.forEach(function (p) { t = t.split(p[0]).join(p[1]); });
    t = t.toLowerCase().split("ё").join("е");
    t = t.replace(gl(N.SPACED_RE), function (m, g1) { return g1.replace(/[\s.\-*_·]/gu, ""); });
    t = t.replace(gl(N.REPEAT_RE), "$1");
    return t;
  }
  function normalize(text) {
    var t = clean(text), c = [], l = [];
    splitWs(t).forEach(function (tok) { var r = fixToken(tok); c.push(r[0]); l.push(r[1]); });
    return [c.join(" ").split("ё").join("е"), l.join(" ")];
  }
  function matchText(text) { var n = normalize(text); return n[0] === n[1] ? n[0] : n[0] + "\n" + n[1]; }
  function sentences(text) { return (text || "").split(gl(N.SENT_SPLIT)).map(function (p) { return pyStrip(p || ""); }).filter(Boolean); }

  /* ── returns.py ───────────────────────────────────────── */
  var PERIODS = E.periods.map(function (p) { return [py(p[0]), p[1]]; });
  function amountR(num, mult) {
    var v = parseFloat(num.split(" ").join("").split(" ").join("").replace(",", "."));
    if (mult) {
      var m = mult.toLowerCase();
      if (/^(к|k|тыс|тис|мың)/.test(m)) v *= 1000;
      else if (/^(млн|миллион)/.test(m)) v *= 1000000;
    }
    return v;
  }
  function periodDays(word, count) {
    if (!word) return null;
    for (var i = 0; i < PERIODS.length; i++) if (match(PERIODS[i][0], word)) return PERIODS[i][1] * (count ? parseFloat(count) : 1);
    return null;
  }
  function annualize(ratio, days) {
    if (days == null || days <= 0) return null;
    var e = (365 / days) * Math.log1p(ratio);
    if (e > Math.log(1e7)) return Infinity;
    return (Math.exp(e) - 1) * 100;
  }
  function RF(snippet, ratio, days, annual) { return { snippet: snippet, ratio: ratio, period_days: days, annual_pct: annual }; }
  function rfLevel(f) {
    if (f.annual_pct == null) return f.ratio >= 1 ? "high" : f.ratio >= 0.3 ? "medium" : "none";
    if (f.annual_pct > 50) return "high";
    if (f.annual_pct > 25) return "medium";
    return "none";
  }
  function fmt0(x) { return (Math.round(x)).toString(); }
  function periodLabel(d) {
    if (d < 1) return "за " + fmt0(d * 24) + " ч";
    if (d === 1) return "в день"; if (d === 7) return "в неделю"; if (d === 30) return "в месяц"; if (d === 365) return "в год";
    return "за " + fmt0(d) + " дн.";
  }
  function rfDescribe(f) {
    var gain = "+" + fmt0(f.ratio * 100) + "%";
    if (f.period_days == null) return "обещано " + gain + " без указания срока";
    var ann = (f.annual_pct == null || !isFinite(f.annual_pct) || f.annual_pct > 1e6) ? "более 1 000 000% годовых" :
      "≈ " + fmt0(f.annual_pct).replace(/\B(?=(\d{3})+(?!\d))/g, " ") + "% годовых";
    return "обещано " + gain + " " + periodLabel(f.period_days) + " → " + ann;
  }
  var GODOV = py("годов");
  function findReturns(text) {
    var out = [];
    finditer(R.PCT_PERIOD, text).forEach(function (m) {
      var ctx = text.slice(Math.max(0, m.index - 40), m.index);
      if (has(R.EXCLUDE_CTX, ctx) || has(GODOV, text.slice(end(m), end(m) + 10))) return;
      var pct = parseFloat(m[1].replace(",", ".")), days = periodDays(m[3], m[2]);
      if (days == null || (days >= 365 && pct < 100)) { if (days === 365) out.push(RF(m[0], pct / 100, 365, pct)); return; }
      out.push(RF(m[0], pct / 100, days, annualize(pct / 100, days)));
    });
    finditer(R.PERIOD_PCT, text).forEach(function (m) {
      var ctx = text.slice(Math.max(0, m.index - 40), m.index);
      if (has(R.EXCLUDE_CTX, ctx) || has(GODOV, text.slice(end(m), end(m) + 10))) return;
      var w = m[1];
      var days = /(дн|ден|сут|күн)/.test(w) ? 1 : /(недел|апта)/.test(w) ? 7 : /(год|жыл)/.test(w) ? 365 : 30;
      var pct = parseFloat(m[2].replace(",", "."));
      out.push(RF(m[0], pct / 100, days, annualize(pct / 100, days)));
    });
    [[R.INVEST_GET, [2, 3], [5, 6]], [R.INVEST_GET_KZ, [1, 2], [4, 5]]].forEach(function (cfg) {
      finditer(cfg[0], text).forEach(function (m) {
        var vin = amountR(m[cfg[1][0]], m[cfg[1][1]]), vout = amountR(m[cfg[2][0]], m[cfg[2][1]]);
        if (vin <= 0 || vout <= vin) return;
        var tail = text.slice(end(m), end(m) + 40), head = text.slice(Math.max(0, m.index - 10), m.index);
        var pm = search(R.PERIOD_NEAR, m[0] + " " + tail);
        var days = pm ? periodDays(pm[2], pm[1]) : null, ratio = vout / vin - 1;
        out.push(RF(chars(pyStrip(head + m[0] + tail)).slice(0, 120).join(""), ratio, days, annualize(ratio, days)));
      });
    });
    var CTXW = /(влож|вклад|инвест|депозит|сумм|деньг|ақша|салым|доход|прибыл|табыс|пайда|вывод|выплат|сал)/;
    finditer(R.MULT, text).forEach(function (m) {
      var k;
      if (m[1]) { k = parseFloat(m[1].replace(",", ".")); if (k <= 1 || k > 1000) return; }
      else k = m[2] ? 2 : 3;
      var ctx = text.slice(Math.max(0, m.index - 50), end(m) + 50);
      if (!CTXW.test(ctx)) return;
      var pm = search(R.PERIOD_NEAR, text.slice(end(m), end(m) + 40));
      var days = pm ? periodDays(pm[2], pm[1]) : null;
      out.push(RF(chars(pyStrip(ctx)).slice(0, 120).join(""), k - 1, days, annualize(k - 1, days)));
    });
    var uniq = [], seen = {};
    out.forEach(function (f) { var key = Math.round(f.ratio * 1000) / 1000 + "|" + f.period_days; if (!seen[key]) { seen[key] = 1; uniq.push(f); } });
    return uniq;
  }

  /* ── signals.py ───────────────────────────────────────── */
  var CATALOG = {};
  E.catalog.forEach(function (d) { CATALOG[d.id] = d; });
  function Unit(msg, orig, norm) { return { msg: msg, orig: orig, norm: norm }; }
  function find(units, rx, limit) {
    limit = limit || 3; var ev = [];
    for (var i = 0; i < units.length; i++) {
      if (has(rx, units[i].norm)) { ev.push({ msg: units[i].msg, text: trim(units[i].orig) }); if (ev.length >= limit) break; }
    }
    return ev;
  }

  function detectText(units, local) {
    var doc = units.map(function (u) { return u.norm; }).join("\n");
    var hits = new Map();
    function add(sid, ev, note) {
      if (!ev || !ev.length) return;
      if (!hits.has(sid)) hits.set(sid, { id: sid, evidence: [], note: "" });
      var h = hits.get(sid);
      ev.forEach(function (e) {
        if (h.evidence.length < 3 && !h.evidence.some(function (x) { return x.msg === e.msg && x.text === e.text; })) h.evidence.push(e);
      });
      if (note && !h.note) h.note = note;
    }
    var giveaway = has(S.GIVEAWAY_CTX, doc), casino = has(S.CASINO_CTX, doc);
    var msgText = new Map();
    units.forEach(function (u) { msgText.set(u.msg, (msgText.get(u.msg) || "") + "\n" + u.norm); });
    var gUnits = local ? units.filter(function (u) { return has(S.GIVEAWAY_CTX, msgText.get(u.msg)); }) : (giveaway ? units : []);
    var cMsgs = new Set();
    if (local) msgText.forEach(function (t, m) { if (has(S.CASINO_CTX, t)) cMsgs.add(m); });
    else if (casino) msgText.forEach(function (t, m) { cMsgs.add(m); });

    // Трек 1
    var paidEv = gUnits.filter(function (u) { return (has(S.PAID_COND, u.norm) && has(S.PAY_WORDS, u.norm)) || has(S.PAID_PRICE, u.norm); })
      .map(function (u) { return { msg: u.msg, text: trim(u.orig) }; });
    paidEv = paidEv.concat(find(gUnits, S.PAID_COURSE));
    add("T1_PAID", paidEv.slice(0, 3));
    if (has(S.PRIZE_FEE, doc) && (has(S.PRIZE_WIN, doc) || has(S.PRIZE_WORDS, doc)))
      add("T1_PRIZE_FEE", find(units, S.PRIZE_WIN, 1).concat(find(units, S.PRIZE_FEE, 2)));
    add("T1_WIN_DM", find(units, S.PRIZE_WIN, 2));
    var baitEv = find(units, S.BAIT, 2);
    if (!baitEv.length && has(S.BIG_SUM, doc) && (has(S.URGENCY, doc) || has(S.PRIZE_WORDS, doc))) baitEv = find(units, S.BIG_SUM, 1);
    add("T1_BAIT", baitEv);
    if (baitEv.length && has(S.BIG_SUM, doc)) add("T1_BIG_SUM", find(units, S.BIG_SUM, 1));
    add("T1_RANDOM", find(units, S.RANDOM));
    add("T1_ORG_INCOME", find(gUnits, S.ORG_INCOME));
    add("T1_POT", find(units, S.POT));
    add("T1_REGULAR", find(gUnits, S.REGULAR, 2));

    // Трек 2
    add("T2_PROMO", find(units.filter(function (u) { return cMsgs.has(u.msg); }), S.PROMO));
    add("T2_PROMO", find(units, S.DEPOSIT_BONUS));
    add("T2_LINK", find(units, S.LINK));
    add("T2_NATIVE_WIN", find(units, S.NATIVE_WIN));
    add("T2_GAMBLING", find(units, S.GAMBLING));
    var bcMsgs = [];
    if (local) msgText.forEach(function (t, m) { if (has(S.BOOKMAKER, t) && has(S.GAMBLING, t)) bcMsgs.push(m); });
    else if (has(S.BOOKMAKER, doc) && has(S.GAMBLING, doc)) msgText.forEach(function (t, m) { bcMsgs.push(m); });
    if (bcMsgs.length) {
      var bcUnits = units.filter(function (u) { return bcMsgs.indexOf(u.msg) >= 0; });
      add("T2_BRAND_COVER", find(bcUnits, S.BOOKMAKER, 1).concat(find(bcUnits, S.GAMBLING, 1)));
    }
    add("T2_CHANNEL", find(units, S.CHANNEL));
    add("T2_CHANNEL", units.filter(function (u) { return has(S.CHANNEL_DM, u.norm) && has(S.MONEY_CTX, msgText.get(u.msg)); })
      .map(function (u) { return { msg: u.msg, text: trim(u.orig) }; }).slice(0, 2));
    add("T2_MIRROR", find(units, S.MIRROR));
    var dset = {};
    units.forEach(function (u) { finditer(S.DOMAIN_RE, u.norm).forEach(function (m) { dset[m[1]] = 1; }); });
    var domains = Object.keys(dset).sort(), bases = new Map();
    domains.forEach(function (d) {
      var b = d.split(".")[0].replace(/[\d-]+/g, "");
      if (!bases.has(b)) bases.set(b, []);
      bases.get(b).push(d);
    });
    bases.forEach(function (ds, base) {
      if (ds.length >= 2 && chars(base).length >= 4) {
        add("T2_MIRROR", units.filter(function (u) { return ds.some(function (d) { return u.norm.indexOf(d) >= 0; }); })
          .map(function (u) { return { msg: u.msg, text: trim(u.orig) }; }).slice(0, 2), "Похожие домены: " + ds.slice().sort().join(", "));
      }
    });

    // Трек 3
    var best = null, msgUnits = new Map();
    units.forEach(function (u) {
      if (!msgUnits.has(u.msg)) msgUnits.set(u.msg, Unit(u.msg, "", ""));
      var mu = msgUnits.get(u.msg);
      mu.orig = pyStrip(mu.orig + " " + u.orig);
      mu.norm = pyStrip(mu.norm + " " + u.norm.split("\n").join(" "));
    });
    var pool = units.slice();
    msgUnits.forEach(function (m) { if (m.norm) pool.push(m); });
    pool.forEach(function (u) {
      findReturns(u.norm).forEach(function (f) {
        var lv = rfLevel(f);
        if (lv === "none") return;
        var rank = [lv === "high", f.annual_pct == null ? 0 : (f.annual_pct || 0)];
        if (!best || (rank[0] !== best[0][0] ? rank[0] : rank[1] > best[0][1])) best = [rank, f, u];
      });
    });
    if (best) {
      add(rfLevel(best[1]) === "high" ? "T3_RETURN" : "T3_RETURN_MED", [{ msg: best[2].msg, text: trim(best[2].orig) }], rfDescribe(best[1]));
    }
    add("T3_GUARANTEE", find(units, S.GUARANTEE));
    add("T3_REFERRAL", find(units, S.REFERRAL));
    add("T3_URGENCY", find(units, S.URGENCY));
    add("T3_LEGEND", find(units, S.LEGEND, 2));
    add("T3_REINVEST", find(units, S.REINVEST));
    add("T3_PAYOUT_PROOF", find(units, S.PAYOUT, 2));
    add("T3_DENIAL", find(units, S.DENIAL, 3).filter(function (e) { return !/\?$/.test(e.text.replace(/\s+$/u, "")); }).slice(0, 1));
    add("T3_EASY_INCOME", find(units, S.EASY_INCOME, 2));
    add("T3_INVEST_CALL", find(units, S.INVEST_CALL, 1));
    add("T3_NEW_MONEY", find(units, S.NEW_MONEY, 2));

    add("X_CARD", units.filter(function (u) { return has(S.CARD, u.norm) && !(has(S.OUTGOING, u.norm) && !has(S.REQUEST, u.norm)); })
      .map(function (u) { return { msg: u.msg, text: trim(u.orig) }; }).slice(0, 3));
    if (has(S.GIVE_MONEY, doc) && has(S.PICK_VIEWERS, doc) && has(S.MOVE_CHANNEL, doc))
      add("T1_WARMUP", find(units, S.GIVE_MONEY, 1).concat(find(units, S.PICK_VIEWERS, 1), find(units, S.MOVE_CHANNEL, 1)));
    add("X_PAY_TO_GET", find(units, S.PAY_TO_GET, 2));
    add("X_WITHDRAW_FEE", find(units, S.WITHDRAW_FEE, 2));

    detectConcepts(units, add, local);
    if (has(S.PROMO, doc) && hits.has("T2_NATIVE_WIN")) add("T2_PROMO", find(units, S.PROMO, 1));

    var moneyFlow = ["T1_PAID", "T1_POT", "X_CARD", "X_PAY_TO_GET", "T1_PRIZE_FEE"].some(function (k) { return hits.has(k); });
    if (has(S.CHARITY, doc) && moneyFlow) add("T1_CHARITY", find(units, S.CHARITY, 2));
    if (has(S.FREE, doc) && (hits.has("T1_PAID") || hits.has("T1_POT")))
      add("T1_FUNNEL", find(units, S.FREE, 1).concat((hits.get("T1_PAID") || hits.get("T1_POT")).evidence.slice(0, 1)));

    add("D_WARNING", find(units, S.WARNING, 2));
    add("D_OFFICIAL", find(units, S.OFFICIAL, 1));
    add("D_LICENSED_FIN", find(units, S.LICENSED, 1));
    add("D_EDU", find(units, S.EDU, 1));

    var msgSet = new Set(units.map(function (u) { return u.msg; }));
    if (msgSet.size > 1) {
      var posMsgs = new Set();
      hits.forEach(function (h, sid) { if (CATALOG[sid].points > 0) h.evidence.forEach(function (e) { if ((e.msg == null ? -1 : e.msg) >= 0) posMsgs.add(e.msg); }); });
      var DRX = { D_WARNING: S.WARNING, D_OFFICIAL: S.OFFICIAL, D_LICENSED_FIN: S.LICENSED, D_EDU: S.EDU, D_FREE: S.FREE };
      Array.from(hits.keys()).filter(function (s) { return CATALOG[s].points < 0; }).forEach(function (sid) {
        var ev = hits.get(sid).evidence.filter(function (e) { return posMsgs.has(e.msg); });
        if (!ev.length) {
          for (var i = 0; i < units.length; i++) {
            if (posMsgs.has(units[i].msg) && has(DRX[sid], units[i].norm)) { ev = [{ msg: units[i].msg, text: trim(units[i].orig) }]; break; }
          }
        }
        if (ev.length) hits.get(sid).evidence = ev.slice(0, 2); else hits.delete(sid);
      });
    }
    if (has(S.FREE, doc) && !moneyFlow) add("D_FREE", find(units, S.FREE, 1));
    return hits;
  }

  /* ── concepts.py ──────────────────────────────────────── */
  var VYIGR = /(выигр|приз|казино|слот|ставк)/;
  function firstNotNeg(rx, text) {
    var ms = finditer(rx, text);
    for (var i = 0; i < ms.length; i++) if (!has(C.NEG, text.slice(Math.max(0, ms[i].index - 25), ms[i].index))) return ms[i];
    return null;
  }
  function shortQ(s) { return trim(s, 180); }
  function detectConcepts(units, add, local) {
    var byMsg = new Map();
    units.forEach(function (u) { if (!byMsg.has(u.msg)) byMsg.set(u.msg, []); byMsg.get(u.msg).push(u); });
    var doc = units.map(function (u) { return u.norm; }).join("\n");
    var giveawayDoc = has(C.GIVEAWAY, doc);
    byMsg.forEach(function (us, msg) {
      var text = us.map(function (u) { return u.norm; }).join(" ");
      var quote = [{ msg: msg, text: shortQ(us.map(function (u) { return u.orig; }).join(" ")) }];
      var freeHere = has(C.FREE, text);
      var giveawayHere = local ? has(C.GIVEAWAY, text) : giveawayDoc;
      var pay = firstNotNeg(C.PAY, text);
      if (pay) {
        var gain = null, gs = finditer(C.GAIN, text, end(pay));
        for (var i = 0; i < gs.length; i++) if (!has(C.NEG, text.slice(Math.max(0, gs[i].index - 25), gs[i].index))) { gain = gs[i]; break; }
        if (gain && (search(C.MORE, text, gain.index) || search(C.MONEY, text, gain.index)) && !freeHere &&
          !has(C.NOT_PROFIT, text.slice(gain.index, gain.index + 40))) add("X_PAY_TO_GET", quote, "сочетание: оплата → выгода → больше");
      }
      if (has(C.WITHDRAW, text) && firstNotNeg(C.FEE, text) && has(C.COND, text)) add("X_WITHDRAW_FEE", quote, "сочетание: вывод + доплата + условие");
      if (giveawayHere && !freeHere) {
        var part = firstNotNeg(C.PARTICIPATE, text);
        if (part && (firstNotNeg(C.PAY, text) || has(C.MONEY, text))) add("T1_PAID", quote, "сочетание: участие + оплата или сумма");
      }
      var g = firstNotNeg(C.GUARANTEE, text);
      if (g && (has(C.GAIN, text) || has(C.GAMBLING_SLANG, text) || VYIGR.test(text))) add("T3_GUARANTEE", quote, "гарантия выигрыша или дохода");
      if (firstNotNeg(C.GAMBLING_SLANG, text)) add("T2_GAMBLING", quote, "игровой сленг");
      if (firstNotNeg(C.INVITE, text) && has(C.GAIN, text)) {
        add("T3_REFERRAL", quote, "сочетание: приглашение + выгода");
        if (has(C.CONTRIB, text)) add("T3_NEW_MONEY", quote, "сочетание: приглашение + выгода + взносы");
      }
      if (firstNotNeg(C.INCOME, text)) add("T3_EASY_INCOME", quote, "обещание дохода");
      if (giveawayHere && has(C.TERMS, text) && has(C.PRIVATE, text) && !has(C.LEGIT_TERMS, text)) add("T1_HIDDEN_TERMS", quote, "условия не опубликованы, только в личке");
    });
  }

  /* ── scoring.py ───────────────────────────────────────── */
  function anyOf(h, ids) { return ids.some(function (k) { return h.has(k); }); }
  function allOf(h, ids) { return ids.every(function (k) { return h.has(k); }); }
  var COMBO_FN = [
    function (h) { return h.has("T1_PAID") && anyOf(h, ["T1_RANDOM", "T1_ORG_INCOME"]); },
    function (h) { return h.has("T1_POT"); },
    function (h) { return allOf(h, ["T1_REPEAT_WINNER", "T1_SHILL"]); },
    function (h) { return h.has("T1_WARMUP") && anyOf(h, ["T1_PAID", "T1_POT", "X_PAY_TO_GET"]); },
    function (h) { return h.has("T1_PRIZE_FEE") && anyOf(h, ["X_CARD", "T2_LINK", "T3_URGENCY", "T1_RANDOM"]); },
    function (h) { return h.has("T2_PROMO") && anyOf(h, ["T2_NATIVE_WIN", "T2_GAMBLING", "T2_LINK", "T2_CHANNEL"]); },
    function (h) { return h.has("T2_BRAND_COVER") && anyOf(h, ["T2_LINK", "T2_PROMO", "T2_CHANNEL", "T2_NATIVE_WIN"]); },
    function (h) { return allOf(h, ["T2_MIRROR", "T2_GAMBLING"]); },
    function (h) { return allOf(h, ["T2_NATIVE_WIN", "T2_GAMBLING"]) && anyOf(h, ["T2_LINK", "T2_CHANNEL"]); },
    function (h) { return h.has("NET_PROMO") && anyOf(h, ["T2_GAMBLING", "T2_NATIVE_WIN", "T2_PROMO"]); },
    function (h) { return h.has("T3_RETURN") && anyOf(h, ["T3_REFERRAL", "X_CARD", "T3_GUARANTEE", "T3_URGENCY"]); },
    function (h) { return h.has("NET_SCREENSHOT") && anyOf(h, ["T3_RETURN", "T3_RETURN_MED", "T3_GUARANTEE"]); },
    function (h) { return allOf(h, ["T3_REFERRAL", "X_CARD"]) && anyOf(h, ["T3_GUARANTEE", "T3_LEGEND", "T3_REINVEST"]); },
    function (h) { return h.has("T1_PAID") && anyOf(h, ["T3_GUARANTEE", "T1_BAIT"]); },
    function (h) { return h.has("T1_PRIZE_FEE"); },
    function (h) { return h.has("T3_GUARANTEE") && h.has("T2_GAMBLING"); },
    function (h) { return h.has("X_WITHDRAW_FEE"); },
    function (h) { return h.has("X_PAY_TO_GET") && anyOf(h, ["T3_RETURN", "T3_RETURN_MED", "X_CARD", "T1_BAIT"]); },
    function (h) { return h.has("T3_NEW_MONEY") && anyOf(h, ["T3_REFERRAL", "T3_INVEST_CALL", "T3_GUARANTEE", "T3_EASY_INCOME"]); },
    function (h) { return h.has("T3_RETURN") && h.has("T3_GUARANTEE"); }
  ];
  var COMBO_MED_FN = [
    function (h) { return h.has("X_PAY_TO_GET"); },
    function (h) { return h.has("T3_RETURN"); },
    function (h) { return h.has("T1_PAID"); },
    function (h) { return h.has("T1_HIDDEN_TERMS"); },
    function (h) { return h.has("T1_WARMUP"); },
    function (h) { return h.has("T3_EASY_INCOME") && h.has("T3_URGENCY"); },
    function (h) { return h.has("X_CARD") && anyOf(h, ["T3_GUARANTEE", "T3_EASY_INCOME", "X_PAY_TO_GET"]); },
    function (h) { return h.has("T1_BAIT") && anyOf(h, ["T3_URGENCY", "T2_CHANNEL", "X_CARD", "T1_PAID", "T1_WIN_DM", "T2_LINK"]); },
    function (h) { return h.has("T1_WIN_DM"); },
    function (h) { return allOf(h, ["T1_BAIT", "T1_BIG_SUM"]); },
    function (h) { return h.has("T3_EASY_INCOME") && anyOf(h, ["T3_INVEST_CALL", "X_CARD", "T3_REFERRAL", "T3_GUARANTEE", "T3_URGENCY"]); },
    function (h) { return h.has("T3_REFERRAL") && anyOf(h, ["T3_EASY_INCOME", "T3_GUARANTEE", "T3_NEW_MONEY", "T3_RETURN", "T3_RETURN_MED"]); },
    function (h) { return h.has("T3_NEW_MONEY"); },
    function (h) { return h.has("T2_GAMBLING") && anyOf(h, ["T2_PROMO", "T3_RETURN_MED", "T1_BAIT"]); }
  ];
  if (COMBO_FN.length !== E.combo_labels.length || COMBO_MED_FN.length !== E.combo_med_labels.length) throw new Error("Комбинации движка не совпадают с Python");

  function levelOf(risk) { return risk >= 70 ? ["high", "Высокий"] : risk >= 40 ? ["medium", "Средний"] : ["low", "Низкий"]; }
  function score(ids) {
    var pos = 0, neg = 0;
    ids.forEach(function (s) { var p = CATALOG[s].points; if (p > 0) pos += p; else if (p < 0) neg += p; });
    var combos = [], labels70 = {};
    COMBO_FN.forEach(function (fn, i) { if (fn(ids)) { combos.push(E.combo_labels[i]); labels70[E.combo_labels[i][1]] = 1; } });
    var med = [];
    COMBO_MED_FN.forEach(function (fn, i) { if (fn(ids) && !labels70[E.combo_med_labels[i][1]]) med.push(E.combo_med_labels[i]); });
    var base = Math.min(100, pos);
    if (combos.length) base = Math.max(base, E.floor); else if (med.length) base = Math.max(base, E.floor_med);
    var risk = Math.max(0, Math.min(100, base + neg));
    var ts = { 1: 0, 2: 0, 3: 0 };
    ids.forEach(function (s) { var d = CATALOG[s]; if (ts[d.track] !== undefined && d.points > 0) ts[d.track] += d.points; });
    combos.forEach(function (c) { if (c[0]) ts[c[0]] += 40; });
    med.forEach(function (c) { if (c[0]) ts[c[0]] += 20; });
    var bestT = 1; [2, 3].forEach(function (t) { if (ts[t] > ts[bestT]) bestT = t; });
    var track = ts[bestT] > 0 ? bestT : 0, lv = levelOf(risk);
    return { risk: risk, level: lv[0], level_label: lv[1], track: track, track_scores: ts,
      combos: combos.map(function (c) { return c[1]; }), combos_med: combos.length ? [] : med.map(function (c) { return c[1]; }),
      points_positive: pos, points_negative: neg };
  }
  function summary(r) {
    var names = r.signals.filter(function (s) { return s.points > 0; }).slice(0, 4).map(function (s) { return s.title; });
    if (!names.length) return r.level_label + " риск (" + r.risk + "). Признаков схемы не найдено.";
    var tail = r.level !== "low" ? "Требуется ручная проверка." : "Достаточно выборочной проверки.";
    return r.level_label + " риск (" + r.risk + "): " + names.map(function (n) { var a = chars(n); return a[0].toLowerCase() + a.slice(1).join(""); }).join(", ") + ". " + tail;
  }

  /* ── streams.py ───────────────────────────────────────── */
  function counterMax(map) { var bu = null, bn = 0; map.forEach(function (n, u) { if (n > bn) { bn = n; bu = u; } }); return [bu, bn]; }
  function spaced(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " "); }
  function analyzeBids(c, untilT) {
    var bids = (c.bids || []).filter(function (b) { return untilT == null || b.t <= untilT; });
    var winners = (c.winners || []).filter(function (w) { return untilT == null || w.t <= untilT; });
    var rules = c.rules || {}, hits = {};
    var stats = { total_collected: 0, rounds: 0, pot_series: [], last_bidders: {}, win_counts: {} };
    if (!bids.length && !winners.length) return [hits, stats];
    var total = 0;
    bids.slice().sort(function (a, b) { return a.t - b.t; }).forEach(function (b) { total += b.amount; stats.pot_series.push({ t: b.t, total: total }); });
    stats.total_collected = total;
    var byRound = new Map();
    bids.forEach(function (b) { if (!byRound.has(b.round)) byRound.set(b.round, []); byRound.get(b.round).push(b); });
    var roundEnd = new Map();
    winners.forEach(function (w) { roundEnd.set(w.round, w.t); });
    var rs = new Set(); byRound.forEach(function (v, k) { rs.add(k); }); roundEnd.forEach(function (v, k) { rs.add(k); });
    stats.rounds = rs.size;
    var last = new Map(), closed = 0;
    byRound.forEach(function (bs, r) {
      if (!roundEnd.has(r)) return;
      closed++;
      var lb = bs[0]; bs.forEach(function (b) { if (b.t > lb.t) lb = b; });
      if (roundEnd.get(r) - lb.t <= E.snipe_window) last.set(lb.user, (last.get(lb.user) || 0) + 1);
    });
    last.forEach(function (n, u) { stats.last_bidders[u] = n; });
    if (closed >= 3 && last.size) {
      var lm = counterMax(last);
      if (lm[1] / closed >= 0.5 && lm[1] >= 3) hits.T1_SHILL = { evidence: [{ msg: -1, text: lm[0] + ": последняя ставка за ≤" + E.snipe_window + " сек. до конца в " + lm[1] + " из " + closed + " раундов" }], note: lm[1] + "/" + closed + " раундов" };
    }
    var wins = new Map();
    winners.forEach(function (w) { wins.set(w.user, (wins.get(w.user) || 0) + 1); });
    wins.forEach(function (n, u) { stats.win_counts[u] = n; });
    if (wins.size) {
      var wm = counterMax(wins), limit = rules.one_win_per_user ? 2 : 3;
      if (wm[1] >= limit) hits.T1_REPEAT_WINNER = { evidence: [{ msg: -1, text: wm[0] + " выиграл " + wm[1] + " из " + winners.length + " раундов" + (rules.one_win_per_user ? " — правила разрешают побеждать один раз" : "") }], note: wm[1] + " побед из " + winners.length };
    }
    var prize = winners.reduce(function (a, w) { return a + (w.prize || 0); }, 0) || (rules.start_prize || 0) * Math.max(1, winners.length);
    if (prize && total / prize >= 1.5) hits.T1_POT_RATIO = { evidence: [{ msg: -1, text: "Собрано " + spaced(total) + " тг при призах " + spaced(prize) + " тг" }], note: "в " + (total / prize).toFixed(1) + " раза больше" };
    return [hits, stats];
  }

  /* ── pipeline.py ──────────────────────────────────────── */
  function buildUnits(c, upto) {
    var units = [], msgs = c.messages || [];
    for (var i = 0; i < msgs.length; i++) {
      if (upto != null && i > upto) break;
      sentences(msgs[i].text || "").forEach(function (s) { units.push(Unit(i, s, matchText(s))); });
    }
    (c.images || []).forEach(function (img) {
      var i = img.msg || 0;
      if (upto != null && i > upto) return;
      sentences(img.ocr || "").forEach(function (s) { units.push(Unit(i, "[скриншот] " + s, matchText(s))); });
    });
    return units;
  }
  function collect(c, upto) {
    var hits = detectText(buildUnits(c, upto), c.type === "chat");
    if ((c.bids && c.bids.length) || (c.winners && c.winners.length)) {
      var untilT = null;
      if (upto != null && c.messages && c.messages.length) untilT = c.messages[Math.min(upto, c.messages.length - 1)].t;
      var b = analyzeBids(c, untilT)[0];
      Object.keys(b).forEach(function (sid) { hits.set(sid, { id: sid, evidence: b[sid].evidence, note: b[sid].note || "" }); });
    }
    return hits;
  }
  function result(c, hits) {
    var sc = score(new Set(hits.keys())), signals = [];
    hits.forEach(function (h, sid) {
      var d = CATALOG[sid];
      signals.push({ id: sid, title: d.title, hint: d.hint, track: d.track, weight: d.weight, points: d.points, evidence: h.evidence, note: h.note });
    });
    signals.sort(function (a, b) { var ka = a.points > 0 ? -a.points : 1000 - a.points, kb = b.points > 0 ? -b.points : 1000 - b.points; return ka - kb; });
    var res = Object.assign({ id: c.id }, sc, { track_name: E.track_names[sc.track], signals: signals });
    res.summary = summary(res);
    res.legal_hint = sc.level !== "low" ? (E.legal_hint[sc.track] || "") : "";
    return res;
  }
  function analyzeCase(c, upto) {
    var res = result(c, collect(c, upto));
    if ((c.bids && c.bids.length) || (c.winners && c.winners.length)) res.stream = analyzeBids(c)[1];
    return res;
  }
  function analyzeText(text) { return analyzeCase({ id: "manual", type: "post", messages: [{ t: 0, author: "", text: text }] }); }
  function timeline(c) {
    var out = [], prev = new Set();
    (c.messages || []).forEach(function (m, i) {
      var res = result(c, collect(c, i)), ids = new Set(res.signals.map(function (s) { return s.id; }));
      out.push({ msg: i, t: m.t != null ? m.t : i, risk: res.risk, level: res.level, "new": Array.from(ids).filter(function (x) { return !prev.has(x); }).sort() });
      prev = ids;
    });
    return out;
  }
  function firstHigh(tl) { for (var i = 0; i < tl.length; i++) if (tl[i].level === "high") return tl[i].msg; return null; }
  function analyzeInput(text, caseId) {
    var lines = splitlines(text).filter(function (l) { return pyStrip(l); });
    if (lines.length >= 3) {
      var c = parseTranscript(text, caseId || "uploaded");
      if (c.type !== "post") return Object.assign(analyzeCase(c), { "case": c, timeline: timeline(c) });
    }
    return analyzeText(text);
  }
  function subCase(c, s, e) {
    var sub = Object.assign({}, c);
    sub.messages = (c.messages || []).slice(s, e);
    sub.images = (c.images || []).filter(function (i) { return s <= (i.msg || 0) && (i.msg || 0) < e; }).map(function (i) { return Object.assign({}, i, { msg: i.msg - s }); });
    return sub;
  }
  function authorBreakdown(c) {
    var by = new Map();
    (c.messages || []).forEach(function (m, i) { var a = m.author || ""; if (!by.has(a)) by.set(a, []); by.get(a).push(i); });
    var all = buildUnits(c), out = [];
    by.forEach(function (idx, author) {
      var set = new Set(idx), units = all.filter(function (u) { return set.has(u.msg); });
      var hits = detectText(units, true), pos = [];
      hits.forEach(function (h, sid) { if (CATALOG[sid].points > 0) pos.push(CATALOG[sid]); });
      out.push({ author: author, messages: idx.length, points: pos.reduce(function (a, d) { return a + d.points; }, 0),
        signals: pos.slice().sort(function (a, b) { return b.points - a.points; }).slice(0, 4).map(function (d) { return d.title; }) });
    });
    out.sort(function (a, b) { return (b.points - a.points) || (b.messages - a.messages); });
    return out;
  }
  function analyzeChat(c, win, step) {
    win = win || 40; step = step || 20;
    var msgs = c.messages || [], n = msgs.length, start = 0, stop = n;
    if (n > win) {
      var best = null;
      for (var s = 0; s < Math.max(1, n - win + step); s += step) {
        var r = analyzeCase(subCase(c, s, s + win));
        if (!best || r.risk > best[0].risk) best = [r, s];
      }
      start = best[1]; stop = Math.min(n, best[1] + win);
    }
    var sub = subCase(c, start, stop), res = analyzeCase(sub), seen = new Set();
    res.signals.forEach(function (sg) { sg.evidence.forEach(function (e) { if (!seen.has(e) && (e.msg == null ? -1 : e.msg) >= 0) { seen.add(e); e.msg += start; } }); });
    var tl = timeline(sub);
    tl.forEach(function (p) { p.msg += start; });
    res.chat = { messages: n, window: [start, stop - 1], first_high: firstHigh(tl), authors: authorBreakdown(c).slice(0, 8), source: c.source || "" };
    sub.messages = sub.messages.map(function (m) { return Object.assign({}, m); });
    var liveTl = tl.map(function (p) { return Object.assign({}, p, { msg: p.msg - start }); });
    return Object.assign(res, { "case": sub, timeline: liveTl });
  }

  /* ── transcript.py ────────────────────────────────────── */
  var BIDS = E.bid_patterns.map(function (p) { return py(p); });
  var WINS = E.winner_patterns.map(function (p) { return py(p); });
  var PZ = py("(забирает|получает|алады)\\s+" + E.amount);
  function amountT(num, unit) {
    var v = parseFloat(num.split(" ").join("").split(" ").join("").replace(",", "."));
    var u = (unit || "").toLowerCase();
    if (/^(к|k|тыс|тис|мың)/.test(u)) v *= 1000;
    return pyRound(v);
  }
  function parseTranscript(raw, caseId, title) {
    var lines = splitlines(raw).filter(function (l) { return pyStrip(l); });
    var timed = lines.filter(function (l) { return match(T.TIME, l); }).length;
    var hasTime = timed >= Math.max(1, Math.floor(lines.length / 2));
    var messages = [], bids = [], winners = [], rules = {}, rnd = 1, lastT = 0, pot = [];
    lines.forEach(function (line) {
      var t = lastT + 5, m = match(T.TIME, line);
      if (m) {
        var hm = parseInt(m[1], 10), mm = parseInt(m[2], 10), ss = m[3];
        t = ss ? hm * 3600 + mm * 60 + parseInt(ss, 10) : hm * 60 + mm;
        line = line.slice(end(m));
      } else if (hasTime) t = lastT;
      t = Math.max(t, lastT); lastT = t;
      var author = "", a = match(T.AUTHOR, line);
      if (a) { author = a[1]; line = line.slice(end(a)); }
      var text = pyStrip(line);
      messages.push({ t: t, author: author, text: text });
      var low = clean(text), found = false;
      for (var i = 0; i < BIDS.length && !found; i++) {
        finditer(BIDS[i], low).forEach(function (bm) {
          var amt = amountT(bm.groups.num, bm.groups.unit);
          if (amt >= 50 && amt <= 5000000) { bids.push({ t: t, round: rnd, user: bm.groups.user, amount: amt }); found = true; }
        });
      }
      if (!found && author) {
        var sb = match(T.SELF_BID, low);
        if (sb) {
          var amt = amountT(sb[2], sb[3]);
          if (amt >= 50 && amt <= 5000000) bids.push({ t: t, round: rnd, user: (author.charAt(0) === "@" ? author : "@" + author).toLowerCase(), amount: amt });
        }
      }
      if (has(T.ONE_WIN, low)) rules.one_win_per_user = true;
      if (!("start_prize" in rules)) { var pm = T.PRIZE.exec(low); if (pm) rules.start_prize = amountT(pm[4], pm[5]); }
      var pmm = T.POT_MENTION.exec(low);
      if (pmm) pot.push({ t: t, total: amountT(pmm[3], pmm[4]) });
      for (var j = 0; j < WINS.length; j++) {
        var wm = WINS[j].exec(low);
        if (wm) {
          var prize = rules.start_prize || 0, pz = PZ.exec(low);
          if (pz) prize = amountT(pz[2], pz[3]);
          winners.push({ t: t, round: rnd, user: wm.groups.user, prize: prize });
          rnd++; break;
        }
      }
    });
    var rounds = new Set(winners.map(function (w) { return w.round; }));
    return { id: caseId || "uploaded", type: (bids.length >= 3 || winners.length >= 2) ? "stream" : (messages.length > 1 ? "chat" : "post"),
      platform: (bids.length || winners.length) ? "Эфир" : "Чат", account: "@uploaded", title: title || "Загруженный эфир",
      messages: messages, bids: bids, winners: winners, rules: rules, images: [],
      parsed: { bids: bids.length, winners: winners.length, rounds: rounds.size, pot_mentions: pot.slice(-5), has_time: hasTime } };
  }

  /* ── importers.py ─────────────────────────────────────── */
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function fmtDate(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes()); }
  function topAuthor(msgs) {
    var cnt = new Map(); msgs.forEach(function (m) { cnt.set(m.author, (cnt.get(m.author) || 0) + 1); });
    return counterMax(cnt)[0] || "";
  }
  function tgText(t) {
    if (typeof t === "string") return t;
    if (Array.isArray(t)) return t.map(function (x) { return typeof x === "string" ? x : String((x && x.text) || ""); }).join("");
    return "";
  }
  function parseIsoLocal(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/.exec(s || "");
    return m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)) : null;
  }
  function tgChat(chat, idx) {
    var msgs = [], t0 = null, list = chat.messages || [];
    for (var i = 0; i < list.length; i++) {
      var m = list[i];
      if (m.type !== "message") continue;
      var text = pyStrip(tgText(m.text || ""));
      if (m.photo || ["photo", "video_file", "animation"].indexOf(m.media_type) >= 0) text = pyStrip(text + (m.photo ? " [фото]" : " [медиафайл]"));
      if (!text) continue;
      var dt = parseIsoLocal(m.date);
      if (dt && !t0) t0 = dt;
      var t = dt && t0 ? Math.round((dt - t0) / 1000) : msgs.length * 60;
      msgs.push({ t: t, author: String(m.from || m.actor || "канал"), text: text, date: dt ? fmtDate(dt) : "" });
      if (msgs.length >= E.max_messages) break;
    }
    if (!msgs.length) return null;
    return { id: "tg-" + (idx + 1), type: "chat", platform: "Telegram", title: chat.name || ("Чат " + (idx + 1)), account: topAuthor(msgs),
      messages: msgs, images: [], date: msgs[0].date ? msgs[0].date.slice(0, 10) : "", source: "Экспорт Telegram" };
  }
  function parseTelegram(raw) {
    var data = JSON.parse(raw.replace(/^﻿/, ""));
    var chats = data && data.chats && typeof data.chats === "object" && !Array.isArray(data.chats) ? data.chats.list : null;
    chats = (chats && chats.length) ? chats : [data];
    return chats.map(tgChat).filter(Boolean);
  }
  function parseWhatsapp(raw, name) {
    var text = raw.replace(/^﻿/, ""), msgs = [], t0 = null, cur = null;
    var lines = splitlines(text);
    if (lines.length && lines[lines.length - 1] === "") lines.pop();
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i], m = match(I.WA_LINE, line);
      if (m) {
        var a = match(I.WA_AUTHOR, m.groups.rest);
        if (!a) { cur = null; continue; }
        var y = parseInt(m.groups.y, 10); y = y < 100 ? y + 2000 : y;
        var h = parseInt(m.groups.h, 10);
        if (m.groups.ampm) h = h % 12 + (m.groups.ampm.toLowerCase() === "pm" ? 12 : 0);
        var mo = parseInt(m.groups.mo, 10), d = parseInt(m.groups.d, 10), mi = parseInt(m.groups.mi, 10), s = parseInt(m.groups.s || "0", 10);
        var dt = new Date(y, mo - 1, d, h, mi, s);
        if (dt.getMonth() !== mo - 1 || dt.getDate() !== d || h > 23 || mi > 59 || s > 59) dt = null;
        if (dt && !t0) t0 = dt;
        var body = pyStrip(a.groups.text.replace(gl(I.WA_MEDIA), "[медиафайл]"));
        cur = { t: dt && t0 ? Math.round((dt - t0) / 1000) : msgs.length * 60, author: pyStrip(a.groups.a).replace(/^‎+/, ""), text: body, date: dt ? fmtDate(dt) : "" };
        msgs.push(cur);
        if (msgs.length >= E.max_messages) break;
      } else if (cur && pyStrip(line)) cur.text += "\n" + pyStrip(line);
    }
    msgs = msgs.filter(function (x) { return x.text; });
    if (!msgs.length) return [];
    return [{ id: "wa-1", type: "chat", platform: "WhatsApp", title: name || "Чат WhatsApp", account: topAuthor(msgs), messages: msgs, images: [],
      date: msgs[0].date ? msgs[0].date.slice(0, 10) : "", source: "Экспорт WhatsApp" }];
  }
  function loadExport(filename, raw) {
    var head = raw.slice(0, 2000).replace(/^﻿/, "").replace(/^\s+/, "");
    if (/\.json$/i.test(filename) || head.charAt(0) === "{") return parseTelegram(raw);
    var title = filename.split("/").pop().replace(/\.(txt|zip)$/i, "");
    title = pyStrip(title.replace(/^(WhatsApp Chat with|Чат WhatsApp с|Чат WhatsApp с )\s*/, "")) || "Чат WhatsApp";
    return parseWhatsapp(raw, title);
  }

  root.AlayakEngine = { analyzeInput: analyzeInput, analyzeText: analyzeText, analyzeCase: analyzeCase, analyzeChat: analyzeChat,
    loadExport: loadExport, parseTranscript: parseTranscript, normalize: normalize, timeline: timeline, findReturns: findReturns };
})(typeof window !== "undefined" ? window : globalThis);
