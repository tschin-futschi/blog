// 前端搜索：调用 /blog/search?q= 接口，实时显示结果
(function () {
  const input = document.getElementById("search-input");
  const resultsBox = document.getElementById("search-results");
  if (!input || !resultsBox) return;

  let timer = null;

  input.addEventListener("input", function () {
    clearTimeout(timer);
    const q = this.value.trim();

    if (!q) {
      resultsBox.style.display = "none";
      resultsBox.innerHTML = "";
      return;
    }

    // 防抖 300ms
    timer = setTimeout(() => {
      fetch(`/blog/search?q=${encodeURIComponent(q)}`)
        .then((r) => r.json())
        .then((data) => renderResults(data, q))
        .catch(() => {});
    }, 300);
  });

  function renderResults(posts, q) {
    if (!posts.length) {
      resultsBox.innerHTML = `<div class="no-result">没有找到"${escHtml(q)}"相关文章</div>`;
      resultsBox.style.display = "block";
      return;
    }

    resultsBox.innerHTML = posts
      .slice(0, 8)
      .map(
        (p) => `
      <div class="result-item">
        <a href="/blog/${escHtml(p.slug)}">${highlight(p.title, q)}</a>
        <div class="result-meta">
          ${escHtml(p.date_str)}
          ${p.tags.map((t) => `<span class="tag">#${escHtml(t)}</span>`).join(" ")}
        </div>
      </div>`
      )
      .join("");

    resultsBox.style.display = "block";
  }

  function highlight(text, q) {
    const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return escHtml(text).replace(
      new RegExp(escHtml(escaped), "gi"),
      (m) => `<mark>${m}</mark>`
    );
  }

  function escHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // 点击外部关闭搜索结果
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".search-wrap")) {
      resultsBox.style.display = "none";
    }
  });

  // ESC 关闭
  input.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      resultsBox.style.display = "none";
      input.blur();
    }
  });
})();
