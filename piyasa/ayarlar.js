/* Piyasa Hava Durumu — "Kişisel ayar" editor (ayarlar.html, B5). Every change is saved at once to this
   browser only (kisisel.js → localStorage). No network calls. The ayar kodu travels in the #k= hash,
   which browsers never send to a server. DOM APIs only. */
(function () {
  "use strict";
  var K = window.PHD_KISISEL;
  var EN = !!(window.PHD_I18N && window.PHD_I18N.en);
  function L(tr, en) { return EN ? en : tr; }
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    if (EN) e.setAttribute("data-noi18n", "");
    return e;
  }
  if (!K || !$("kis-bolum")) return;

  var pref = K.load() || K.defaults();
  var MODE_LABEL = { on: L("Önde", "First"), normal: L("Normal", "Normal"), gizle: L("Gizle", "Hide") };

  function status(msg) { $("durum").textContent = msg; }
  function link(code) {
    var u = location.origin + location.pathname + (EN ? "?lang=en" : "");
    return u + "#k=" + code;
  }
  function commit(msg) {
    var ok;
    if (K.isDefault(pref)) ok = K.clear(); else ok = K.save(pref);
    status(ok ? (msg || L("Kaydedildi · yalnız bu cihazda.", "Saved · on this device only."))
              : L("Bu tarayıcı kaydetmeye izin vermiyor (gizli pencere olabilir). Ayar yalnız bu sayfa açıkken geçerli.",
                  "This browser does not allow saving (maybe a private window). The setting lasts only while this page is open."));
    render();
  }
  function move(list, i, d) {
    var j = i + d;
    if (j < 0 || j >= list.length) return false;
    var t = list[i]; list[i] = list[j]; list[j] = t;
    return true;
  }
  function arrows(list, i, name, focusKey) {
    var box = el("span", "kis-ok");
    [[-1, "↑", L(name + " yukarı", "Move " + name + " up")], [1, "↓", L(name + " aşağı", "Move " + name + " down")]].forEach(function (x) {
      var b = el("button", "kis-btn kis-sm", x[1]);
      b.type = "button";
      b.setAttribute("aria-label", x[2]);
      b.disabled = (x[0] < 0 && i === 0) || (x[0] > 0 && i === list.length - 1);
      b.addEventListener("click", function () {
        if (move(list, i, x[0])) { commit(); focusAfter(focusKey, x[0]); }
      });
      box.appendChild(b);
    });
    return box;
  }
  // keep keyboard focus on the moved row's same arrow
  var pendingFocus = null;
  function focusAfter(key, d) { pendingFocus = { key: key, d: d }; applyFocus(); }
  function applyFocus() {
    if (!pendingFocus) return;
    var row = document.querySelector('[data-key="' + pendingFocus.key + '"]');
    if (row) {
      var bs = row.querySelectorAll(".kis-ok button");
      var b = bs[pendingFocus.d < 0 ? 0 : 1];
      if (b && b.disabled) b = bs[pendingFocus.d < 0 ? 1 : 0];
      if (b) b.focus();
    }
    pendingFocus = null;
  }

  function render() {
    var ol = $("kis-bolum");
    ol.textContent = "";
    pref.sections.forEach(function (s, i) {
      var spec = K.SECTIONS.filter(function (x) { return x.id === s.id; })[0];
      var name = EN ? spec.en : spec.tr;
      var li = el("li", "kis-row" + (s.hide ? " off" : ""));
      li.setAttribute("data-key", "s-" + s.id);
      li.appendChild(el("span", "kis-n", name));
      var lab = el("label", "kis-chk");
      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = !s.hide;
      cb.addEventListener("change", function () {
        s.hide = !cb.checked;
        var visible = pref.sections.filter(function (x) { return !x.hide; }).length;
        if (!visible) { s.hide = false; status(L("En az bir bölüm görünür kalmalı.", "At least one section must stay visible.")); render(); return; }
        commit();
        var again = document.querySelector('[data-key="s-' + s.id + '"] input');
        if (again) again.focus();
      });
      lab.appendChild(cb);
      lab.appendChild(el("span", null, L("Göster", "Show")));
      li.appendChild(lab);
      li.appendChild(arrows(pref.sections, i, name, "s-" + s.id));
      ol.appendChild(li);
    });

    var ok = $("kis-konu");
    ok.textContent = "";
    pref.topics.forEach(function (t, i) {
      var spec = K.TOPICS.filter(function (x) { return x.k === t.k; })[0];
      var name = EN ? spec.en : spec.k;
      var li = el("li", "kis-row m-" + t.m);
      li.setAttribute("data-key", "t-" + K.TOPICS.indexOf(spec));
      li.appendChild(el("span", "kis-n", name));
      var sel = document.createElement("select");
      sel.className = "kis-sel";
      sel.setAttribute("aria-label", L(name + ": görünüm", name + ": display"));
      K.MODES.forEach(function (m) {
        var o = el("option", null, MODE_LABEL[m]);
        o.value = m;
        if (m === t.m) o.selected = true;
        sel.appendChild(o);
      });
      sel.addEventListener("change", function () {
        t.m = sel.value;
        commit();
        var again = document.querySelector('[data-key="t-' + K.TOPICS.indexOf(spec) + '"] select');
        if (again) again.focus();
      });
      li.appendChild(sel);
      li.appendChild(arrows(pref.topics, i, name, "t-" + K.TOPICS.indexOf(spec)));
      ok.appendChild(li);
    });

    var code = K.encode(pref);
    $("kod").value = code;
  }

  $("kopyala").addEventListener("click", function () {
    var u = link(K.encode(pref));
    var done = function () { status(L("Bağlantı kopyalandı. Öbür cihazda açman yeterli.", "Link copied. Just open it on the other device.")); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(u).then(done, function () { $("kod").value = u; $("kod").select(); status(L("Bağlantıyı seçip kopyala.", "Select and copy the link.")); });
    } else { $("kod").value = u; $("kod").select(); status(L("Bağlantıyı seçip kopyala.", "Select and copy the link.")); }
  });
  function applyCode(raw, fromLink) {
    var s = String(raw || "").trim();
    var m = /#k=([^&\s]+)/.exec(s);
    if (m) s = decodeURIComponent(m[1]);
    var p = K.decode(s);
    if (!p) { status(L("Kod okunamadı. Ayarlar değişmedi.", "Could not read the code. Settings unchanged.")); return; }
    pref = p;
    commit(fromLink ? L("Bağlantıdaki ayarlar bu cihaza kaydedildi.", "Settings from the link were saved on this device.")
                    : L("Kod uygulandı ve bu cihaza kaydedildi.", "Code applied and saved on this device."));
  }
  $("uygula").addEventListener("click", function () { applyCode($("kod-gir").value, false); $("kod-gir").value = ""; });
  $("kod-gir").addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); $("uygula").click(); } });
  $("sifirla").addEventListener("click", function () {
    pref = K.defaults();
    K.clear();
    render();
    status(L("Varsayılan sıra geri geldi; bu cihazdaki ayar silindi.", "Default order restored; the setting on this device was deleted."));
  });

  render();
  var hm = /^#k=([^&]+)/.exec(location.hash);
  if (hm) {
    applyCode(decodeURIComponent(hm[1]), true);
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) { /* ignore */ }
  }
})();
