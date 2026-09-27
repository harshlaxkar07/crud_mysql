/* Student Records — front end for the MySQL student records API. */
(function () {
  "use strict";

  const { $, $$, el, esc, icon, http, toast, modal, initials, debounce } = UI;

  http.base = "";

  let students = [];
  let gradeFilter = "all";

  const BANDS = [
    { name: "Distinction", min: 80, max: 100, color: "var(--ok)" },
    { name: "First class", min: 60, max: 79, color: "var(--accent)" },
    { name: "Pass", min: 40, max: 59, color: "var(--warn)" },
    { name: "Below pass", min: 0, max: 39, color: "var(--danger)" },
  ];

  const gradeClass = (m) => (m >= 80 ? "grade-a" : m >= 60 ? "grade-b" : m >= 40 ? "grade-c" : "grade-d");
  const meterClass = (m) => (m >= 80 ? "ok" : m >= 60 ? "" : m >= 40 ? "warn" : "danger");

  /* ---------------- connection ---------------- */
  async function ping() {
    const node = $("#conn");
    const text = $(".conn-text", node);
    try {
      const data = await http.get("/api/health");
      node.className = "conn online";
      text.textContent = data && data.database ? `Connected · ${data.database}` : "API connected";
    } catch (err) {
      node.className = "conn offline";
      text.textContent = err.status === 503 ? "Database unreachable" : "API unreachable";
    }
  }

  /* ---------------- data ---------------- */
  async function load() {
    try {
      students = await http.get("/api/students");
      if (!Array.isArray(students)) students = [];
    } catch (err) {
      students = [];
      const host = $("#table");
      host.innerHTML = `<div class="empty">
        <div class="empty-icon" style="background:var(--danger-soft);color:var(--danger)">${icon("alert", 24)}</div>
        <h3>Could not load records</h3><p>${esc(err.message)}</p></div>`;
      renderStats();
      return;
    }
    $("[data-count='rec']").textContent = students.length;
    renderStats();
    renderTable();
    renderHistogram();
    renderLeaderboard();
    renderBands();
  }

  /* ---------------- stats ---------------- */
  function renderStats() {
    const marks = students.map((s) => s.marks || 0);
    const avg = marks.length ? marks.reduce((a, b) => a + b, 0) / marks.length : 0;
    const top = marks.length ? Math.max(...marks) : 0;
    const passing = marks.filter((m) => m >= 40).length;

    $("#stats").innerHTML = [
      { label: "Students", value: students.length, hint: "records in the table", ic: "users" },
      { label: "Average marks", value: avg.toFixed(1), hint: "across the class", ic: "chart" },
      { label: "Highest marks", value: top, hint: "top of the class", ic: "award" },
      {
        label: "At or above pass",
        value: passing,
        hint: students.length ? `${Math.round((passing / students.length) * 100)}% of the class` : "no records yet",
        ic: "checkCircle",
      },
    ]
      .map(
        (t) => `<div class="stat">
        <div class="stat-icon">${icon(t.ic, 16)}</div>
        <div class="stat-label">${esc(t.label)}</div>
        <div class="stat-value">${esc(t.value)}</div>
        <div class="stat-hint">${esc(t.hint)}</div></div>`
      )
      .join("");
  }

  /* ---------------- table ---------------- */
  function renderTable() {
    const term = ($("#filter").value || "").toLowerCase();

    const rows = students.filter((s) => {
      const m = s.marks || 0;
      if (gradeFilter === "high" && m < 80) return false;
      if (gradeFilter === "mid" && (m < 40 || m > 79)) return false;
      if (gradeFilter === "low" && m >= 40) return false;
      if (!term) return true;
      return `${s.full_name} ${s.roll_no}`.toLowerCase().includes(term);
    });

    const host = $("#table");
    if (!rows.length) {
      host.innerHTML = `<div class="empty">
        <div class="empty-icon">${icon("users", 24)}</div>
        <h3>${students.length ? "Nothing matches those filters" : "The table is empty"}</h3>
        <p>${students.length ? "Clear the filter to see every record." : "Add your first student record to get started."}</p>
        ${students.length ? "" : `<button class="btn btn-primary" id="emptyAdd">${icon("plus", 15)} Add student</button>`}
      </div>`;
      const b = $("#emptyAdd");
      if (b) b.addEventListener("click", () => editStudent(null));
      return;
    }

    host.innerHTML = `
      <div class="table-wrap"><table class="table">
        <thead><tr><th>Student</th><th class="num">Roll no</th><th class="num">Marks</th><th>Band</th><th class="num">ID</th><th></th></tr></thead>
        <tbody>${rows
          .map((s) => {
            const m = s.marks || 0;
            const band = BANDS.find((b) => m >= b.min && m <= b.max) || BANDS[3];
            return `
          <tr>
            <td>
              <div class="student-cell">
                <div class="avatar">${esc(initials(s.full_name))}</div>
                <div class="sb"><div class="sn truncate">${esc(s.full_name || "—")}</div>
                <div class="sr">Roll ${esc(s.roll_no)}</div></div>
              </div>
            </td>
            <td class="num">${esc(s.roll_no)}</td>
            <td>
              <div class="marks-cell">
                <div class="marks-bar"><div class="meter ${meterClass(m)}"><span style="width:${m}%"></span></div></div>
                <div class="marks-value ${gradeClass(m)}">${m}</div>
              </div>
            </td>
            <td class="nowrap"><span class="badge" style="color:${band.color}">${esc(band.name)}</span></td>
            <td class="num mono">${esc(s.id)}</td>
            <td class="actions">
              <button class="btn btn-sm btn-ghost" data-edit="${s.id}" title="Edit">${icon("edit", 13)}</button>
              <button class="btn btn-sm btn-ghost" data-del="${s.id}" title="Delete">${icon("trash", 13)}</button>
            </td>
          </tr>`;
          })
          .join("")}</tbody></table></div>`;

    $$("#table [data-edit]").forEach((b) =>
      b.addEventListener("click", () => editStudent(Number(b.dataset.edit)))
    );
    $$("#table [data-del]").forEach((b) =>
      b.addEventListener("click", () => removeStudent(Number(b.dataset.del)))
    );
  }

  /* ---------------- insights ---------------- */
  function renderHistogram() {
    const buckets = Array.from({ length: 10 }, () => 0);
    students.forEach((s) => {
      const i = Math.min(9, Math.floor((s.marks || 0) / 10));
      buckets[i]++;
    });

    const max = Math.max(...buckets, 1);
    const host = $("#histogram");

    if (!students.length) {
      host.innerHTML = `<p class="muted small">The distribution appears once records have been added.</p>`;
      return;
    }

    host.innerHTML = `<div class="histogram">${buckets
      .map(
        (count, i) => `
      <div class="hbar" title="${i * 10}–${i * 10 + 9}: ${count} student${count === 1 ? "" : "s"}">
        <div class="hbar-track">
          <div class="hbar-fill" style="height:${count ? Math.max((count / max) * 100, 4) : 0}%">
            ${count ? `<span class="hbar-count">${count}</span>` : ""}
          </div>
        </div>
        <div class="hbar-label">${i * 10}</div>
      </div>`
      )
      .join("")}</div>`;
  }

  function renderLeaderboard() {
    const top = students.slice().sort((a, b) => (b.marks || 0) - (a.marks || 0)).slice(0, 6);
    const host = $("#leaderboard");

    if (!top.length) {
      host.innerHTML = `<div class="empty" style="padding:30px 20px">
        <div class="empty-icon">${icon("award", 24)}</div>
        <h3>No records yet</h3><p>The leaderboard fills in as students are added.</p></div>`;
      return;
    }

    host.innerHTML = top
      .map(
        (s, i) => `
      <div class="lb-row">
        <div class="lb-rank">${i + 1}</div>
        <div class="avatar">${esc(initials(s.full_name))}</div>
        <div class="lb-body">
          <div class="lb-name truncate">${esc(s.full_name || "—")}</div>
          <div class="lb-roll">Roll ${esc(s.roll_no)}</div>
        </div>
        <div class="lb-marks ${gradeClass(s.marks || 0)}">${esc(s.marks ?? 0)}</div>
      </div>`
      )
      .join("");
  }

  function renderBands() {
    $("#bands").innerHTML = BANDS.map((b) => {
      const count = students.filter((s) => (s.marks || 0) >= b.min && (s.marks || 0) <= b.max).length;
      return `<div class="band" style="--bc:${b.color}">
        <div class="band-name">${esc(b.name)}</div>
        <div class="band-count">${count}</div>
        <div class="band-range">${b.min}–${b.max} marks</div>
      </div>`;
    }).join("");
  }

  /* ---------------- create / edit ---------------- */
  function editStudent(id) {
    const s = id === null ? null : students.find((x) => x.id === id);

    const form = el("form", { class: "stack" });
    form.innerHTML = `
      <div class="field">
        <label>Full name</label>
        <input class="input" name="full_name" required maxlength="30" value="${esc(s ? s.full_name : "")}" placeholder="Student's full name">
      </div>
      <div class="field">
        <label>Roll number</label>
        <input class="input" name="roll_no" type="number" required min="0" value="${esc(s ? s.roll_no : "")}" placeholder="e.g. 42">
      </div>
      <div class="field">
        <label>Marks</label>
        <input class="input" name="marks" type="number" required min="0" max="100" value="${esc(s ? s.marks : "")}" placeholder="0 to 100">
        <span class="hint">Out of 100</span>
      </div>`;

    modal({
      title: s ? `Edit ${s.full_name}` : "Add a student",
      body: form,
      actions: [
        { label: "Cancel", onClick: (close) => close() },
        {
          label: s ? "Save changes" : "Add student",
          variant: "primary",
          onClick: async (close, btn) => {
            if (!form.reportValidity()) return;
            btn.classList.add("loading");

            const data = new FormData(form);
            const payload = {
              full_name: String(data.get("full_name")).trim(),
              roll_no: Number(data.get("roll_no")),
              marks: Number(data.get("marks")),
            };

            try {
              if (s) await http.put(`/api/students/${s.id}`, payload);
              else await http.post("/api/students", payload);
              toast(s ? "Record updated" : "Student added", "success");
              close();
              load();
            } catch (err) {
              toast(err.message, "error");
            } finally {
              btn.classList.remove("loading");
            }
          },
        },
      ],
    });
  }

  async function removeStudent(id) {
    const s = students.find((x) => x.id === id);
    const ok = await UI.confirm({
      title: "Delete this record?",
      message: `${s ? s.full_name : "This student"} will be removed from the table.`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      const res = await http.del(`/api/students/${id}`);
      toast(res && res.message ? res.message : "Record deleted", "success");
      load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function clearAll() {
    if (!students.length) {
      toast("The table is already empty", "info");
      return;
    }
    const ok = await UI.confirm({
      title: "Clear the whole table?",
      message: `All ${students.length} records will be removed.`,
      confirmLabel: "Clear table",
      danger: true,
    });
    if (!ok) return;
    try {
      const res = await http.del("/api/students");
      toast(res && res.message ? res.message : "Table cleared", "success");
      load();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  /* ---------------- boot ---------------- */
  function init() {
    UI.shell({ start: "records" });

    $("#addBtn").addEventListener("click", () => editStudent(null));
    $("#clearAll").addEventListener("click", clearAll);
    $("#filter").addEventListener("input", debounce(renderTable, 180));

    $$("#gradeFilter button").forEach((b) =>
      b.addEventListener("click", () => {
        gradeFilter = b.dataset.grade;
        $$("#gradeFilter button").forEach((x) => x.classList.toggle("active", x === b));
        renderTable();
      })
    );

    $("#refresh").addEventListener("click", async (e) => {
      e.currentTarget.classList.add("loading");
      await Promise.all([ping(), load()]);
      e.currentTarget.classList.remove("loading");
      toast("Records reloaded", "success");
    });

    ping();
    load();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
