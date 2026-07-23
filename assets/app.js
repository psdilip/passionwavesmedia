/* PassionWavesMedia — shared front-end behavior.
   Config is injected by the build as window.PW = { supabaseUrl, supabaseAnonKey }. */
(function () {
  var cfg = window.PW || {};
  var haveDB = !!(cfg.supabaseUrl && cfg.supabaseAnonKey);

  /* ---------- scroll reveal ---------- */
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });

  /* ---------- category filter (cards are static; we just show/hide) ---------- */
  window.pwFilter = function (btn, cat) {
    document.querySelectorAll(".filters .chip").forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
    btn.setAttribute("aria-pressed", "true");
    document.querySelectorAll("#grid .card").forEach(function (card) {
      card.style.display = (cat === "all" || card.dataset.cat === cat) ? "flex" : "none";
    });
    var feat = document.getElementById("featured");
    if (feat) feat.style.display = (cat === "all") ? "" : "none";
  };

  /* ---------- Supabase helper ---------- */
  function rpc(fn, args) {
    return fetch(cfg.supabaseUrl + "/rest/v1/rpc/" + fn, {
      method: "POST",
      headers: {
        "apikey": cfg.supabaseAnonKey,
        "Authorization": "Bearer " + cfg.supabaseAnonKey,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(args)
    }).then(function (r) { if (!r.ok) throw new Error("rpc"); return r.json(); });
  }

  function fmt(n) {
    if (n == null) return "—";
    if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, "") + "k";
    return String(n);
  }

  /* ---------- likes + views on an article page ---------- */
  window.pwInitArticle = function (slug) {
    var likeBtn = document.getElementById("likeBtn");
    var likeCount = document.getElementById("likeCount");
    var viewCount = document.getElementById("viewCount");
    if (!likeBtn) return;

    var likedKey = "pw_liked_" + slug;
    var alreadyLiked = localStorage.getItem(likedKey) === "1";
    if (alreadyLiked) likeBtn.classList.add("liked");

    // Register a view + load counts.
    if (haveDB) {
      rpc("pw_view", { p_slug: slug })
        .then(function (rows) {
          var row = Array.isArray(rows) ? rows[0] : rows;
          if (row) { likeCount.textContent = fmt(row.likes); viewCount.textContent = fmt(row.views) + " reads"; }
        })
        .catch(function () { viewCount.textContent = ""; });
    } else {
      // Local fallback: no shared counts, but the button still works visually.
      viewCount.textContent = "";
      likeCount.textContent = alreadyLiked ? "1" : "0";
    }

    likeBtn.addEventListener("click", function () {
      if (localStorage.getItem(likedKey) === "1") return; // one like per browser
      localStorage.setItem(likedKey, "1");
      likeBtn.classList.add("liked", "pop");
      setTimeout(function () { likeBtn.classList.remove("pop"); }, 360);

      if (haveDB) {
        rpc("pw_like", { p_slug: slug })
          .then(function (rows) { var row = Array.isArray(rows) ? rows[0] : rows; if (row) likeCount.textContent = fmt(row.likes); })
          .catch(function () {});
      } else {
        likeCount.textContent = String((parseInt(likeCount.textContent, 10) || 0) + 1);
      }
    });
  };
  /* ---------- sidebar navigator (articles.html) ---------- */
  window.pwArchiveInitV2 = function () {
    var gridEl = document.getElementById("arcGrid");
    if (!gridEl) return;
    var posts = window.PW_POSTS || [];
    var cats = window.PW_CATS || {};
    var quotes = window.PW_QUOTES || [];
    var catNames = Object.keys(cats);

    var state = { q: "", cat: "All", sort: "new" };
    var initHash = decodeURIComponent((location.hash || "").replace("#", ""));
    if (initHash && catNames.indexOf(initHash) !== -1) state.cat = initHash;

    /* rotating quote */
    var quoteEl = document.getElementById("arcQuote");
    if (quoteEl && quotes.length) {
      var qi = 0;
      var showQuote = function () {
        quoteEl.style.opacity = 0;
        setTimeout(function () {
          var q = quotes[qi % quotes.length];
          var text = (typeof q === "string") ? q : q.text;
          var slug = (q && typeof q === "object") ? q.slug : null;
          var link = slug ? '<a class="arc-quote-link" href="' + slug + '.html">Read the piece →</a>' : "";
          quoteEl.innerHTML = "“" + text + "”" + link;
          quoteEl.style.opacity = 1;
          qi++;
        }, 260);
      };
      showQuote();
      var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!reduce && quotes.length > 1) setInterval(showQuote, 7000);
    } else if (quoteEl) {
      quoteEl.remove();
    }

    var navEl = document.getElementById("arcNav");
    var emptyEl = document.getElementById("arcEmpty");
    var countEl = document.getElementById("arcCount");
    var headingEl = document.getElementById("arcHeadingTitle");

    function cardHtml(p) {
      var col = cats[p.category] || "#999";
      var thumb = p.thumb
        ? '<div class="c-thumb"><img src="' + p.thumb + '" alt="" loading="lazy" ' +
          'onerror="this.closest(\'.c-thumb\').classList.add(\'c-thumb--fallback\')">' +
          '<div class="c-thumb-fallback" style="--tc:' + col + '"><span>' + p.category + "</span></div></div>"
        : '<div class="c-thumb c-thumb--fallback"><div class="c-thumb-fallback" style="--tc:' + col + '"><span>' + p.category + "</span></div></div>";
      var tags = (p.tags || []).slice(0, 4).map(function (t) {
        return '<span class="tagchip">' + t + "</span>";
      }).join("");
      return '<a href="' + p.slug + '.html" class="card reveal in" data-cat="' + p.category + '">' + thumb +
        '<div class="card-body"><span class="catline mono"><span class="dot" style="background:' + col + '"></span>' + p.category + "</span>" +
        "<h3>" + p.title + "</h3><p>" + p.excerpt + "</p>" +
        '<div class="tags">' + tags + "</div>" +
        '<div class="foot mono"><span>' + p.date + " · " + p.minutes + " min</span></div></div></a>";
    }

    function renderNav() {
      var html = '<button class="arc-navbtn' + (state.cat === "All" ? " active" : "") + '" data-cat="All">' +
        '<span class="lbl">All</span><span class="n">' + posts.length + "</span></button>";
      catNames.forEach(function (c) {
        var n = posts.filter(function (p) { return p.category === c; }).length;
        html += '<button class="arc-navbtn' + (state.cat === c ? " active" : "") + '" data-cat="' + c + '">' +
          '<span class="lbl"><span class="dot" style="background:' + cats[c] + '"></span>' + c + '</span>' +
          '<span class="n">' + n + "</span></button>";
      });
      navEl.innerHTML = html;
      navEl.querySelectorAll(".arc-navbtn").forEach(function (btn) {
        btn.addEventListener("click", function () {
          state.cat = btn.dataset.cat;
          history.replaceState(null, "", state.cat === "All" ? "#" : "#" + state.cat);
          render();
        });
      });
    }

    function render() {
      renderNav();
      var q = state.q.trim().toLowerCase();
      var list = posts.filter(function (p) {
        if (state.cat !== "All" && p.category !== state.cat) return false;
        if (!q) return true;
        var hay = (p.title + " " + p.excerpt + " " + (p.tags || []).join(" ")).toLowerCase();
        return hay.indexOf(q) !== -1;
      });
      if (state.sort === "new") list.sort(function (a, b) { return b.iso.localeCompare(a.iso); });
      if (state.sort === "old") list.sort(function (a, b) { return a.iso.localeCompare(b.iso); });
      if (state.sort === "quick") list.sort(function (a, b) { return a.minutes - b.minutes; });

      headingEl.textContent = state.cat === "All" ? "All articles" : state.cat;
      countEl.textContent = list.length + (list.length === 1 ? " article" : " articles");
      if (list.length) {
        gridEl.hidden = false; emptyEl.hidden = true;
        gridEl.innerHTML = list.map(cardHtml).join("");
      } else {
        gridEl.hidden = true; emptyEl.hidden = false;
      }
    }

    var searchEl = document.getElementById("arcSearch");
    if (searchEl) searchEl.addEventListener("input", function (e) { state.q = e.target.value; render(); });
    var sortEl = document.getElementById("arcSort");
    if (sortEl) sortEl.addEventListener("change", function (e) { state.sort = e.target.value; render(); });

    render();
  };
})();
