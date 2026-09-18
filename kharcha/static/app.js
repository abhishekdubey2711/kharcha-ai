"use strict";
const $ = (id) => document.getElementById(id);
const money = (paise) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(paise / 100);
const escapeHTML = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const colors = [
  "#315b44",
  "#91ad71",
  "#c8d69c",
  "#e2c790",
  "#d7a489",
  "#9cabb6",
  "#bbacce",
  "#b5bcb4",
];
const icons = {
  1: "☕",
  2: "↗",
  3: "▣",
  4: "⌂",
  5: "♫",
  6: "▤",
  7: "＋",
  8: "◇",
  9: "↓",
  10: "⌘",
  11: "↓",
  12: "↓",
};
const state = {
  categories: [],
  rows: [],
  kind: "",
  page: 1,
  total: 0,
  sequence: 0,
  summarySequence: 0,
  deleteId: null,
};
const dialog = $("transaction-dialog");
let toastTimer;
function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    $("toast").hidden = true;
  }, 4000);
}
function errorIn(id, message) {
  $(id).textContent = message;
  $(id).hidden = !message;
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content,
      ...options.headers,
    },
  });
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Please sign in again.");
  }
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok)
    throw new Error(body.error || "Something went wrong. Please try again.");
  return body;
}
function params() {
  const p = new URLSearchParams({
    month: $("month").value,
    kind: state.kind,
    page: state.page,
    per_page: 10,
    q: $("search").value.trim(),
  });
  if ($("filter-category").value)
    p.set("category_id", $("filter-category").value);
  return p;
}
function svgElement(tag, attrs = {}, text) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  if (text !== undefined) el.textContent = text;
  return el;
}
function drawCashFlow(trend) {
  const svg = svgElement("svg", {
    viewBox: "0 0 540 210",
    role: "img",
    "aria-label": trend
      .map(
        (m) =>
          `${m.month}: income ${money(m.income)}, expenses ${money(m.expense)}`,
      )
      .join("; "),
  });
  const max = Math.max(100000, ...trend.flatMap((m) => [m.income, m.expense]));
  for (let i = 0; i < 4; i++) {
    let y = 15 + i * 52;
    svg.append(
      svgElement("line", {
        x1: 49,
        y1: y,
        x2: 531,
        y2: y,
        stroke: "#edf0e9",
        "stroke-dasharray": "3 4",
      }),
    );
    let val = (max * (3 - i)) / 3;
    svg.append(
      svgElement(
        "text",
        { x: 0, y: y + 4 },
        val >= 100000
          ? `₹${+(val / 100000).toFixed(1)}k`
          : `₹${Math.round(val / 100)}`,
      ),
    );
  }
  trend.forEach((m, i) => {
    let x = 76 + i * 79;
    for (const [j, key] of ["income", "expense"].entries()) {
      let height = (m[key] / max) * 156;
      svg.append(
        svgElement("rect", {
          x: x + j * 21,
          y: 171 - height,
          width: 15,
          height: Math.max(height, 0),
          rx: 3,
          fill: j ? "#1b5142" : "#b4ce8f",
        }),
      );
    }
    svg.append(
      svgElement(
        "text",
        { x: x + 18, y: 198, "text-anchor": "middle" },
        new Date(`${m.month}-01T12:00:00`).toLocaleDateString("en-IN", {
          month: "short",
        }),
      ),
    );
  });
  $("cash-chart").replaceChildren(svg);
}
function drawCategories(categories, total) {
  const svg = svgElement("svg", {
    viewBox: "0 0 180 180",
    role: "img",
    "aria-label": `Monthly spending ${money(total)}`,
  });
  svg.append(
    svgElement("circle", {
      cx: 90,
      cy: 90,
      r: 70,
      fill: "none",
      stroke: "#eff2eb",
      "stroke-width": 18,
    }),
  );
  let offset = 0;
  const length = 2 * Math.PI * 70;
  categories.forEach((c, i) => {
    let segment = (c.total / total) * length;
    svg.append(
      svgElement("circle", {
        cx: 90,
        cy: 90,
        r: 70,
        fill: "none",
        stroke: colors[i % colors.length],
        "stroke-width": 18,
        "stroke-dasharray": `${Math.max(0, segment - 3)} ${length - Math.max(0, segment - 3)}`,
        "stroke-dashoffset": -offset,
        transform: "rotate(-90 90 90)",
      }),
    );
    offset += segment;
  });
  svg.append(
    svgElement(
      "text",
      { x: 90, y: 83, "text-anchor": "middle", "font-size": 10 },
      "TOTAL SPENT",
    ),
  );
  svg.append(
    svgElement(
      "text",
      {
        x: 90,
        y: 105,
        "text-anchor": "middle",
        "font-size": total >= 100000000 ? 13 : 20,
        "font-weight": 650,
      },
      money(total),
    ),
  );
  $("donut").replaceChildren(svg);
  $("category-legend").replaceChildren();
  if (!categories.length) {
    $("category-legend").textContent =
      "No expenses this month. Your next transaction will show up here.";
    return;
  }
  categories.forEach((c, i) => {
    let row = document.createElement("div");
    row.className = "category-row";
    let dot = svgElement("svg", {
      viewBox: "0 0 8 8",
      class: "category-dot",
      "aria-hidden": "true",
    });
    dot.append(
      svgElement("rect", {
        width: 8,
        height: 8,
        rx: 2,
        fill: colors[i % colors.length],
      }),
    );
    let label = document.createElement("span");
    label.textContent = c.name;
    let amount = document.createElement("strong");
    amount.textContent = `${Math.round((c.total / total) * 100)}%`;
    row.title = money(c.total);
    row.append(dot, label, amount);
    $("category-legend").append(row);
  });
}
async function loadSummary() {
  const sequence = ++state.summarySequence;
  const data = await api(
    "/api/summary?" + new URLSearchParams({ month: $("month").value }),
  );
  if (sequence !== state.summarySequence) return;
  $("balance").textContent = money(data.balance_paise);
  $("income").textContent = money(data.income_paise);
  $("expense").textContent = money(data.expense_paise);
  $("net").textContent = money(data.net_paise);
  $("net-caption").textContent =
    data.income_paise > 0 && data.net_paise >= 0
      ? `${Math.round((data.net_paise / data.income_paise) * 100)}% of income kept this month`
      : "Income minus expenses";
  drawCashFlow(data.trend);
  drawCategories(data.categories, data.expense_paise);
}
async function loadTransactions() {
  const sequence = ++state.sequence;
  const data = await api("/api/transactions?" + params());
  if (sequence !== state.sequence) return;
  state.rows = data.transactions;
  state.total = data.total;
  if (!state.rows.length && state.page > 1) {
    state.page--;
    return loadTransactions();
  }
  $("transaction-count").textContent = data.total;
  $("transaction-rows").innerHTML = state.rows.length
    ? state.rows
        .map(
          (t) =>
            `<tr><td><div class="transaction-description"><span class="transaction-icon" aria-hidden="true">${icons[t.category_id] || "◇"}</span><span>${escapeHTML(t.description)}</span></div></td><td><span class="category-pill">${escapeHTML(t.category)}</span></td><td>${new Date(t.date + "T12:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}</td><td>${escapeHTML(t.payment_method)}</td><td class="amount-col amount-value ${t.kind === "income" ? "income" : ""}">${t.kind === "income" ? "+" : "−"}${money(t.amount_paise)}</td><td><div class="row-actions"><button class="icon-button" data-edit="${t.id}" aria-label="Edit ${escapeHTML(t.description)}" title="Edit transaction">✎</button><button class="icon-button" data-delete="${t.id}" aria-label="Delete ${escapeHTML(t.description)}" title="Delete transaction">×</button></div></td></tr>`,
        )
        .join("")
    : '<tr><td colspan="6" class="empty-state">No transactions here yet. Add a transaction or try different filters.</td></tr>';
  $("pagination-label").textContent = data.total
    ? `Showing ${(state.page - 1) * 10 + 1}–${Math.min(state.page * 10, data.total)} of ${data.total} transactions`
    : "0 transactions";
  $("previous").disabled = state.page <= 1;
  $("next").disabled = state.page * 10 >= data.total;
  $("export").href = "/api/export?" + params();
}
async function refresh() {
  errorIn("page-error", "");
  try {
    await Promise.all([loadSummary(), loadTransactions()]);
  } catch (error) {
    errorIn("page-error", error.message);
  }
}
function populateCategories(selected) {
  $("category").replaceChildren();
  state.categories
    .filter((c) => c.kind === $("kind").value)
    .forEach((c) => {
      $("category").add(new Option(c.name, c.id));
    });
  if (selected) $("category").value = selected;
}
function openForm(transaction = null, notice = "") {
  $("transaction-form").reset();
  $("record-id").value = transaction?.id || "";
  $("dialog-title").textContent = transaction?.id
    ? "Edit transaction"
    : notice
      ? "Review your draft"
      : "Add transaction";
  $("kind").value = transaction?.kind || "expense";
  populateCategories(transaction?.category_id);
  if (!transaction) {
    const d = new Date();
    $("date").value =
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }
  if (transaction) {
    for (const [id, key] of [
      ["amount", "amount"],
      ["date", "date"],
      ["description", "description"],
      ["notes", "notes"],
      ["payment", "payment_method"],
    ])
      $(id).value = transaction[key] ?? "";
  }
  $("draft-notice").textContent = notice;
  $("draft-notice").hidden = !notice;
  errorIn("form-error", "");
  dialog.showModal();
  $("amount").focus();
}
$("add-transaction").addEventListener("click", () => openForm());
$("kind").addEventListener("change", () => populateCategories());
for (const button of document.querySelectorAll("[data-close]"))
  button.addEventListener("click", () => dialog.close());
$("transaction-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("save-button");
  button.disabled = true;
  errorIn("form-error", "");
  const record = {
    kind: $("kind").value,
    amount: $("amount").value,
    category_id: Number($("category").value),
    description: $("description").value,
    date: $("date").value,
    payment_method: $("payment").value,
    notes: $("notes").value,
  };
  const id = $("record-id").value;
  try {
    await api("/api/transactions" + (id ? "/" + id : ""), {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(record),
    });
    dialog.close();
    toast(id ? "Transaction updated." : "Transaction saved.");
    await refresh();
  } catch (error) {
    errorIn("form-error", error.message);
  } finally {
    button.disabled = false;
  }
});
$("transaction-rows").addEventListener("click", (event) => {
  const edit = event.target.closest("[data-edit]");
  const remove = event.target.closest("[data-delete]");
  if (edit)
    openForm(state.rows.find((t) => t.id === Number(edit.dataset.edit)));
  if (remove) {
    state.deleteId = Number(remove.dataset.delete);
    $("delete-description").textContent = state.rows.find(
      (t) => t.id === state.deleteId,
    ).description;
    errorIn("delete-error", "");
    $("delete-dialog").showModal();
    $("cancel-delete").focus();
  }
});
$("cancel-delete").addEventListener("click", () => {
  $("delete-dialog").close();
  state.deleteId = null;
});
$("confirm-delete").addEventListener("click", async () => {
  const button = $("confirm-delete");
  button.disabled = true;
  try {
    await api("/api/transactions/" + state.deleteId, { method: "DELETE" });
    $("delete-dialog").close();
    toast("Transaction deleted.");
    await refresh();
  } catch (error) {
    errorIn("delete-error", error.message);
  } finally {
    button.disabled = false;
  }
});
$("quick-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("parse-button");
  button.disabled = true;
  button.textContent = "Preparing…";
  try {
    const data = await api("/api/parse", {
      method: "POST",
      body: JSON.stringify({ text: $("quick-text").value }),
    });
    openForm(data.draft, data.notice);
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Make a draft ↗";
  }
});
$("month").addEventListener("change", () => {
  if (!$("month").value) {
    errorIn("page-error", "Choose a month.");
    return;
  }
  state.page = 1;
  refresh();
});
function filtered() {
  state.page = 1;
  loadTransactions().catch((error) => errorIn("page-error", error.message));
}
for (const button of document.querySelectorAll("[data-kind]"))
  button.addEventListener("click", () => {
    state.kind = button.dataset.kind;
    for (const tab of document.querySelectorAll("[data-kind]")) {
      tab.classList.toggle("selected", tab === button);
      tab.setAttribute("aria-pressed", tab === button ? "true" : "false");
    }
    filtered();
  });
let searchTimer;
$("search").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(filtered, 220);
});
$("filter-category").addEventListener("change", filtered);
$("previous").addEventListener("click", () => {
  state.page--;
  loadTransactions().catch((error) => errorIn("page-error", error.message));
});
$("next").addEventListener("click", () => {
  state.page++;
  loadTransactions().catch((error) => errorIn("page-error", error.message));
});
for (const link of document.querySelectorAll(".nav-link"))
  link.addEventListener("click", () => {
    for (const other of document.querySelectorAll(".nav-link"))
      other.classList.toggle("active", other === link);
  });
(async () => {
  try {
    const data = await api("/api/categories");
    state.categories = data.categories;
    data.categories.forEach((c) =>
      $("filter-category").add(new Option(c.name, c.id)),
    );
    populateCategories();
    await refresh();
  } catch (error) {
    errorIn("page-error", error.message);
  }
})();
