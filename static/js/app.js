// ---------- helpers ----------
async function api(url, data) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data || {}),
  });
  let body = {};
  try { body = await res.json(); } catch (e) { /* non-JSON response */ }
  if (res.status === 401) {                       // not logged in -> go to login
    window.location = "/login?next=" + encodeURIComponent(window.location.pathname);
  }
  return { ok: res.ok, status: res.status, data: body };
}

function toast(message, type) {
  const t = document.getElementById("toast");
  t.textContent = message;
  t.className = "show " + (type || "");
  setTimeout(() => { t.className = ""; }, 3000);
}

function on(selector, handler) {            // attach a click handler to all matching elements
  document.querySelectorAll(selector).forEach(el => el.addEventListener("click", () => handler(el)));
}

// ---------- book details: quantity + add to cart ----------
on(".add-to-cart-quick", async (btn) => {
  const r = await api("/api/cart/add", {
    book_id: parseInt(btn.dataset.bookId, 10),
    quantity: 1,
  });
  if (r.ok) {
    toast(r.data.message, "success");
    const c = document.getElementById("cart-count");
    if (c) c.textContent = r.data.cart_count;
  } else if (r.status !== 401) {
    toast(r.data.error || "Something went wrong", "error");
  }
});

const qtyInput = document.getElementById("qty");
if (qtyInput) {
  const max = parseInt(qtyInput.max, 10);
  document.getElementById("qty-minus").onclick = () => { qtyInput.value = Math.max(1, (parseInt(qtyInput.value, 10) || 1) - 1); };
  document.getElementById("qty-plus").onclick = () => { qtyInput.value = Math.min(max, (parseInt(qtyInput.value, 10) || 0) + 1); };
  document.getElementById("add-to-cart").onclick = async (e) => {
    const r = await api("/api/cart/add", {
      book_id: parseInt(e.target.dataset.bookId, 10),
      quantity: qtyInput.value,           // the server validates this value
    });
    if (r.ok) {
      toast(r.data.message, "success");
      document.getElementById("cart-count").textContent = r.data.cart_count;
    } else if (r.status !== 401) {
      toast(r.data.error || "Something went wrong", "error");
    }
  };
}

// ---------- cart page ----------
on(".cart-qty", async (btn) => {
  const r = await api("/api/cart/update", { item_id: parseInt(btn.dataset.item, 10), quantity: btn.dataset.qty });
  if (r.ok) location.reload(); else toast(r.data.error, "error");
});
on(".cart-remove", async (btn) => {
  const r = await api("/api/cart/remove", { item_id: parseInt(btn.dataset.item, 10) });
  if (r.ok) location.reload(); else toast(r.data.error, "error");
});

// ---------- checkout ----------
const checkoutForm = document.getElementById("checkout-form");
if (checkoutForm) {
  checkoutForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    document.querySelectorAll(".err").forEach(el => el.textContent = "");
    const payload = Object.fromEntries(new FormData(checkoutForm).entries());
    const r = await api("/api/checkout", payload);
    if (r.ok) { window.location = r.data.redirect; return; }
    const errors = r.data.errors || {};
    Object.keys(errors).forEach(k => {
      const el = document.querySelector('.err[data-for="' + k + '"]');
      if (el) el.textContent = errors[k];
    });
    toast(r.data.error || "Could not place order", "error");
  });
}

// ---------- simulated payment ----------
async function pay(orderId, result) {
  const box = document.getElementById("pay-error");
  box.style.display = "none";
  const r = await api("/api/payment/" + orderId + "/simulate", { result: result });
  if (r.ok && r.data.redirect) { window.location = r.data.redirect; return; }
  if (r.ok && r.data.failed) {
    box.textContent = "Payment failed (simulated). No stock was reduced. You can retry.";
    box.style.display = "block";
    setTimeout(() => location.reload(), 1500);   // reload to show the attempt history
    return;
  }
  box.textContent = r.data.error || "Payment error";
  box.style.display = "block";
  if (r.data.redirect) setTimeout(() => { window.location = r.data.redirect; }, 1500);
}
const paySuccess = document.getElementById("pay-success");
if (paySuccess) {
  paySuccess.onclick = () => pay(paySuccess.dataset.order, "success");
  const payFail = document.getElementById("pay-fail");
  payFail.onclick = () => pay(payFail.dataset.order, "failed");
}

// ---------- admin ----------
on(".stock-save", async (btn) => {
  const id = btn.dataset.book;
  const r = await api("/admin/books/" + id + "/stock", { stock: document.getElementById("stock-" + id).value });
  toast(r.ok ? r.data.message : r.data.error, r.ok ? "success" : "error");
});
on(".book-delete", async (btn) => {
  if (!confirm("Delete this book permanently?")) return;
  const r = await api("/admin/books/" + btn.dataset.book + "/delete");
  if (r.ok) { document.getElementById("book-row-" + btn.dataset.book).remove(); toast(r.data.message, "success"); }
  else toast(r.data.error, "error");
});
on(".status-save", async (btn) => {
  const id = btn.dataset.order;
  const r = await api("/admin/orders/" + id + "/status", { status: document.getElementById("newstatus-" + id).value });
  if (r.ok) { toast(r.data.message, "success"); setTimeout(() => location.reload(), 700); }
  else toast(r.data.error, "error");
});
on(".order-request", async (btn) => {
  const action = btn.dataset.request.toLowerCase();
  if (!confirm("Send a " + action + " request for this order?")) return;
  const r = await api("/api/orders/" + btn.dataset.order + "/requests", { request_type: btn.dataset.request });
  if (r.ok) { toast(r.data.message, "success"); setTimeout(() => location.reload(), 700); }
  else toast(r.data.error, "error");
});
on(".request-resolve", async (btn) => {
  const action = btn.dataset.decision;
  if (!confirm(action.charAt(0).toUpperCase() + action.slice(1) + " this customer request?")) return;
  const r = await api("/admin/order-requests/" + btn.dataset.request + "/resolve", { decision: action });
  if (r.ok) { toast(r.data.message, "success"); setTimeout(() => location.reload(), 700); }
  else toast(r.data.error, "error");
});

// ---------- real book covers (Open Library) ----------
// For books with no image URL, look up the cover by title + author.
// If anything fails (offline, no cover found) the generated CSS cover simply stays.
async function loadCover(box) {
  const key = "cover:" + box.dataset.title + "|" + box.dataset.author;
  let url = null;
  try { url = localStorage.getItem(key); } catch (e) {}
  if (url === null) {
    try {
      const author = box.dataset.author.split(",")[0];
      const q = "https://openlibrary.org/search.json?limit=1&fields=cover_i&title=" +
                encodeURIComponent(box.dataset.title) + "&author=" + encodeURIComponent(author);
      const data = await (await fetch(q)).json();
      const id = data.docs && data.docs[0] && data.docs[0].cover_i;
      url = id ? "https://covers.openlibrary.org/b/id/" + id + "-L.jpg?default=false" : "";
      try { localStorage.setItem(key, url); } catch (e) {}
    } catch (e) { return; }
  }
  if (!url) return;
  const img = new Image();
  img.className = "real";
  img.alt = "Cover of " + box.dataset.title;
  img.onload = () => box.appendChild(img);   // only show it if it really loaded
  img.src = url;
}
document.querySelectorAll(".auto-cover").forEach(loadCover);
