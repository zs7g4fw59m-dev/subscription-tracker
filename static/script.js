// ---- State ----
const state = {
    subs: [],
    detectedItems: [],
    currentFilter: { category: "", status: "active" },
};

const COLOR_MAP = {
    "AI工具": "#6366f1", "视频娱乐": "#f43f5e", "音乐": "#8b5cf6",
    "云存储": "#3b82f6", "阅读": "#10b981", "效率工具": "#f59e0b",
    "游戏": "#ec4899", "教育": "#14b8a6", "健身": "#f97316",
    "购物": "#f97316", "社群": "#8b5cf6", "开发服务": "#6366f1",
    "其他": "#64748b",
};

const CYCLE_LABELS = { monthly: "月", yearly: "年", quarterly: "季", weekly: "周", lifetime: "永久" };
const STATUS_LABELS = { active: "活跃", paused: "暂停", cancelled: "取消" };

// ---- API ----
async function api(path, opts = {}) {
    const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `HTTP ${res.status}`);
    }
    return res.json();
}

// ---- Render ----
function renderStats(stats) {
    document.getElementById("statMonthly").textContent = `¥${stats.total_monthly.toLocaleString()}`;
    document.getElementById("statYearly").textContent = `¥${stats.total_yearly.toLocaleString()}`;
    document.getElementById("statActive").textContent = stats.active_count;
    document.getElementById("statTotal").textContent = stats.total_count;
}

function renderCategories(stats) {
    const container = document.getElementById("categoryBreakdown");
    if (!stats.category_breakdown.length) { container.innerHTML = ""; return; }
    container.innerHTML = stats.category_breakdown
        .map(c => `<span class="cat-chip" data-cat="${c.category}">${catIcon(c.category)} ${c.category} <span class="cat-amount">¥${c.total.toLocaleString()}</span></span>`)
        .join("");
    container.querySelectorAll(".cat-chip").forEach(el => {
        el.addEventListener("click", () => {
            const cat = el.dataset.cat;
            state.currentFilter.category = state.currentFilter.category === cat ? "" : cat;
            document.getElementById("filterCategory").value = state.currentFilter.category;
            el.classList.toggle("active", state.currentFilter.category === cat);
            loadSubs();
        });
    });
}

function renderSubs(subs) {
    const container = document.getElementById("subList");
    const empty = document.getElementById("emptyState");
    if (!subs.length) { container.innerHTML = ""; empty.style.display = "block"; return; }
    empty.style.display = "none";
    container.innerHTML = subs.map(s => {
        const monthly = toMonthly(s.amount, s.cycle);
        const cnyMonthly = toMonthly(toCNY(s.amount, s.currency), s.cycle);
        const isForeign = s.currency !== "CNY";
        return `<div class="sub-card" data-id="${s.id}">
            <div class="sub-icon" style="background:${COLOR_MAP[s.category] || COLOR_MAP["其他"]}">${catIcon(s.category)}</div>
            <div class="sub-info">
                <div class="sub-name">${esc(s.name)}</div>
                <div class="sub-meta">${s.category} · ${CYCLE_LABELS[s.cycle] || s.cycle}${s.next_renewal ? ` · 续费 ${s.next_renewal}` : ""}</div>
            </div>
            <div class="sub-amount">
                <div class="amount-value">${currencySymbol(s.currency)}${s.amount.toLocaleString()}</div>
                ${isForeign ? `<div class="amount-cny">≈ ¥${cnyMonthly.toLocaleString()}/月</div>` : `<div class="amount-cycle">/ ${CYCLE_LABELS[s.cycle] || s.cycle}</div>`}
            </div>
            <span class="sub-status status-${s.status}">${STATUS_LABELS[s.status]}</span>
        </div>`;
    }).join("");
    container.querySelectorAll(".sub-card").forEach(card => {
        card.addEventListener("click", () => openEdit(parseInt(card.dataset.id)));
    });
}

function renderUpcoming(stats) {
    const container = document.getElementById("upcomingList");
    if (!stats.upcoming.length) {
        container.innerHTML = '<div class="empty-state" style="padding:20px"><p>暂无即将续费的订阅</p></div>';
        return;
    }
    container.innerHTML = stats.upcoming.map(s => `
        <div class="upcoming-item">
            <span class="upcoming-date">${s.next_renewal || "-"}</span>
            <span class="upcoming-name">${esc(s.name)}</span>
            <span class="upcoming-amount">${currencySymbol(s.currency)}${s.amount.toLocaleString()}</span>
        </div>`).join("");
}

function renderCategoryFilter(cats) {
    const sel = document.getElementById("filterCategory");
    sel.innerHTML = '<option value="">全部分类</option>' + cats.map(c => `<option value="${c}">${c}</option>`).join("");
    document.getElementById("categoryList").innerHTML = cats.map(c => `<option value="${c}">`).join("");
}

// ---- Load data ----
async function loadAll() {
    const [stats, subs, cats] = await Promise.all([
        api("/api/stats"),
        api(`/api/subscriptions?category=${state.currentFilter.category}&status=${state.currentFilter.status}`),
        api("/api/categories"),
    ]);
    state.subs = subs;
    renderStats(stats);
    renderCategories(stats);
    renderSubs(subs);
    renderUpcoming(stats);
    renderCategoryFilter(cats);
}

async function loadSubs() {
    const subs = await api(`/api/subscriptions?category=${state.currentFilter.category}&status=${state.currentFilter.status}`);
    state.subs = subs;
    renderSubs(subs);
}

// ---- Helpers ----
function catIcon(cat) {
    const icons = { AI工具: "🤖", 视频娱乐: "📺", 音乐: "🎵", 云存储: "☁️", 阅读: "📖", 效率工具: "⚡", 游戏: "🎮", 教育: "🎓", 健身: "💪", 购物: "🛒", 社群: "👥", 开发服务: "🔧" };
    return icons[cat] || "📌";
}
const FX = { CNY: 1, USD: 7.2, EUR: 7.8, HKD: 0.92 };

function currencySymbol(c) { return { CNY: "¥", USD: "$", EUR: "€", HKD: "HK$" }[c] || c; }
function toCNY(amount, currency) { return Math.round(amount * (FX[currency] || 1) * 100) / 100; }
function toMonthly(amount, cycle) {
    const rates = { monthly: 1, yearly: 1 / 12, quarterly: 1 / 3, weekly: 4.33, lifetime: 0 };
    return Math.round(amount * (rates[cycle] || 1) * 100) / 100;
}
function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
function fmoney(n) { return Number(n || 0).toFixed(2); }

// ---- Subscription modal ----
function openModal(title, data = null) {
    document.getElementById("modalTitle").textContent = title;
    document.getElementById("modalOverlay").classList.add("show");
    document.getElementById("btnDelete").style.display = data ? "inline-block" : "none";
    document.getElementById("subId").value = data ? data.id : "";
    document.getElementById("subName").value = data ? data.name : "";
    document.getElementById("subAmount").value = data ? data.amount : "";
    document.getElementById("subCurrency").value = data ? data.currency : "CNY";
    document.getElementById("subCycle").value = data ? data.cycle : "monthly";
    document.getElementById("subCategory").value = data ? data.category : "";
    document.getElementById("subRenewal").value = data ? (data.next_renewal || "") : "";
    document.getElementById("subStatus").value = data ? data.status : "active";
    document.getElementById("subNotes").value = data ? (data.notes || "") : "";
}
function closeModal() { document.getElementById("modalOverlay").classList.remove("show"); }
function openEdit(id) { const s = state.subs.find(s => s.id === id); if (s) openModal("编辑订阅", s); }
async function saveSub(e) {
    e.preventDefault();
    const id = document.getElementById("subId").value;
    const body = {
        name: document.getElementById("subName").value,
        amount: parseFloat(document.getElementById("subAmount").value),
        currency: document.getElementById("subCurrency").value,
        cycle: document.getElementById("subCycle").value,
        category: document.getElementById("subCategory").value || "其他",
        next_renewal: document.getElementById("subRenewal").value || null,
        status: document.getElementById("subStatus").value,
        notes: document.getElementById("subNotes").value,
    };
    if (id) {
        await api(`/api/subscriptions/${id}`, { method: "PUT", body: JSON.stringify(body) });
    } else {
        await api("/api/subscriptions", { method: "POST", body: JSON.stringify(body) });
    }
    closeModal();
    loadAll();
}
async function deleteSub() {
    const id = document.getElementById("subId").value;
    if (!id || !confirm("确认删除？")) return;
    await api(`/api/subscriptions/${id}`, { method: "DELETE" });
    closeModal();
    loadAll();
}

// ---- CSV import ----
function openCsvModal() { document.getElementById("csvModalOverlay").classList.add("show"); }
function closeCsvModal() { document.getElementById("csvModalOverlay").classList.remove("show"); resetCsvUI(); }
function resetCsvUI() {
    document.getElementById("uploadZone").style.display = "flex";
    document.getElementById("csvProgress").style.display = "none";
    document.getElementById("csvStatus").innerHTML = "";
    document.getElementById("csvFileInput").value = "";
}
async function handleCsvUpload(file) {
    document.getElementById("uploadZone").style.display = "none";
    document.getElementById("csvProgress").style.display = "flex";
    document.getElementById("csvStatus").innerHTML = "";

    const form = new FormData();
    form.append("file", file);
    try {
        const res = await fetch("/api/import/csv", { method: "POST", body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "导入失败");
        showScanResults("CSV 账单分析结果", data);
        closeCsvModal();
    } catch (err) {
        document.getElementById("csvProgress").style.display = "none";
        document.getElementById("csvStatus").innerHTML = `<div class="error-msg">${esc(err.message)}</div>`;
        document.getElementById("uploadZone").style.display = "flex";
    }
}

// ---- Email scan ----
function openEmailModal() { document.getElementById("emailModalOverlay").classList.add("show"); }
function closeEmailModal() {
    document.getElementById("emailModalOverlay").classList.remove("show");
    document.getElementById("emailError").style.display = "none";
    document.getElementById("emailProgress").style.display = "none";
}
async function startEmailScan() {
    const host = document.getElementById("emailHost").value;
    const emailAddr = document.getElementById("emailAddr").value.trim();
    const password = document.getElementById("emailPass").value.trim();
    if (!emailAddr || !password) {
        document.getElementById("emailError").textContent = "请填写邮箱地址和密码";
        document.getElementById("emailError").style.display = "block";
        return;
    }
    document.getElementById("emailError").style.display = "none";
    document.getElementById("emailProgress").style.display = "flex";
    document.getElementById("btnEmailStart").disabled = true;

    try {
        await api("/api/email/config", { method: "POST", body: JSON.stringify({ host, email: emailAddr, password }) });
        const data = await api("/api/email/scan", { method: "POST", body: JSON.stringify({ days: 90 }) });
        showScanResults("邮箱扫描结果", data);
        closeEmailModal();
    } catch (err) {
        document.getElementById("emailError").textContent = err.message;
        document.getElementById("emailError").style.display = "block";
    } finally {
        document.getElementById("emailProgress").style.display = "none";
        document.getElementById("btnEmailStart").disabled = false;
    }
}

// ---- Scan results ----
function showScanResults(title, data) {
    state.detectedItems = data.subscriptions || [];
    document.getElementById("scanModalTitle").textContent = title;
    const body = document.getElementById("scanModalBody");

    if (state.detectedItems.length === 0) {
        body.innerHTML = `<div class="empty-state" style="padding:40px"><p>😔 未检测到订阅记录</p><p class="empty-hint">换个数据源试试，或手动添加</p></div>
            <div class="form-actions"><div></div><button class="btn" onclick="closeScanModal()">关闭</button></div>`;
    } else {
        body.innerHTML = `
            <p class="help-text">共识别到 <strong>${state.detectedItems.length}</strong> 笔可能的订阅。勾选需要导入的项目。</p>
            <div class="detected-list">${state.detectedItems.map((item, i) => `
                <label class="detected-item">
                    <input type="checkbox" checked data-index="${i}">
                    <div class="detected-info">
                        <div class="detected-name">${esc(item.name)} <span class="tag tag-${item.category}">${item.category || "其他"}</span></div>
                        <div class="detected-meta">
                            ${currencySymbol(item.currency)}${fmoney(item.amount)} / ${CYCLE_LABELS[item.cycle] || item.cycle}
                            ${item.occurrences ? ` · 出现 ${item.occurrences} 次` : ""}
                            ${item.date_range ? ` · ${item.date_range}` : ""}
                            ${item.subject ? ` · ${esc(item.subject)}` : ""}
                        </div>
                    </div>
                </label>`).join("")}</div>
            <div class="form-actions">
                <div><label class="select-all"><input type="checkbox" id="selectAll" checked> 全选</label></div>
                <div class="form-actions-right">
                    <button class="btn" onclick="closeScanModal()">取消</button>
                    <button class="btn btn-primary" id="btnBatchImport">导入选中 (<span id="selectedCount">${state.detectedItems.length}</span>)</button>
                </div>
            </div>`;
    }

    document.getElementById("scanModalOverlay").classList.add("show");

    // Select-all binding
    const selectAll = document.getElementById("selectAll");
    if (selectAll) {
        selectAll.addEventListener("change", () => updateSelectedCount());
        document.querySelectorAll(".detected-item input[type=checkbox]").forEach(cb => {
            cb.addEventListener("change", () => updateSelectedCount());
        });
    }
    const btnImport = document.getElementById("btnBatchImport");
    if (btnImport) btnImport.addEventListener("click", batchImportSelected);
}

function updateSelectedCount() {
    const checks = document.querySelectorAll(".detected-item input[type=checkbox]");
    const all = document.getElementById("selectAll");
    const count = [...checks].filter(c => c.checked).length;
    document.getElementById("selectedCount").textContent = count;
    if (all) all.checked = count === checks.length;
}

async function batchImportSelected() {
    const checks = document.querySelectorAll(".detected-item input[type=checkbox]");
    const items = [];
    checks.forEach(cb => {
        if (cb.checked) {
            const idx = parseInt(cb.dataset.index);
            items.push(state.detectedItems[idx]);
        }
    });
    if (!items.length) return;
    const btn = document.getElementById("btnBatchImport");
    btn.disabled = true;
    btn.textContent = "导入中...";
    try {
        const data = await api("/api/subscriptions/batch-import", { method: "POST", body: JSON.stringify({ items }) });
        closeScanModal();
        loadAll();
        // flash message
        showToast(`已导入 ${data.imported} 笔订阅`);
    } catch (err) {
        alert("导入失败: " + err.message);
        btn.disabled = false;
        btn.textContent = "导入选中";
    }
}

function closeScanModal() { document.getElementById("scanModalOverlay").classList.remove("show"); }

function showToast(msg) {
    let toast = document.getElementById("toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "toast";
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.className = "toast show";
    setTimeout(() => toast.classList.remove("show"), 2500);
}

// ---- Smart text parse ----
function openSmartModal() { document.getElementById("smartModalOverlay").classList.add("show"); }
function closeSmartModal() {
    document.getElementById("smartModalOverlay").classList.remove("show");
    document.getElementById("smartError").style.display = "none";
    document.getElementById("smartProgress").style.display = "none";
    document.getElementById("smartTextInput").value = "";
}
async function submitSmartParse() {
    const text = document.getElementById("smartTextInput").value.trim();
    if (!text) {
        document.getElementById("smartError").textContent = "请粘贴账单文字";
        document.getElementById("smartError").style.display = "block";
        return;
    }
    document.getElementById("smartError").style.display = "none";
    document.getElementById("smartProgress").style.display = "flex";
    document.getElementById("btnSmartSubmit").disabled = true;
    try {
        const data = await api("/api/parse/text", { method: "POST", body: JSON.stringify({ text }) });
        showScanResults("智能识别结果", data);
        closeSmartModal();
    } catch (err) {
        document.getElementById("smartError").textContent = err.message;
        document.getElementById("smartError").style.display = "block";
    } finally {
        document.getElementById("smartProgress").style.display = "none";
        document.getElementById("btnSmartSubmit").disabled = false;
    }
}

// ---- SMS upload ----
async function handleSmsUpload(file) {
    document.getElementById("smartProgress").style.display = "flex";
    document.getElementById("smartError").style.display = "none";
    const form = new FormData();
    form.append("file", file);
    try {
        const res = await fetch("/api/import/sms", { method: "POST", body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "导入失败");
        showScanResults("短信备份分析结果", data);
        closeSmartModal();
    } catch (err) {
        document.getElementById("smartError").textContent = err.message;
        document.getElementById("smartError").style.display = "block";
    } finally {
        document.getElementById("smartProgress").style.display = "none";
    }
}

// ---- Auto-scan ----
async function runAutoScan() {
    showToast("正在自动扫描...");
    try {
        const data = await api("/api/auto-scan", { method: "POST" });
        if (data.subscriptions.length > 0) {
            showScanResults("自动扫描结果", data);
        } else {
            showToast("未发现新的订阅");
        }
    } catch (err) {
        showToast("自动扫描失败: " + err.message);
    }
}

// ---- Event bindings ----
document.getElementById("btnAdd").addEventListener("click", () => openModal("添加订阅"));
document.getElementById("modalClose").addEventListener("click", closeModal);
document.getElementById("btnCancel").addEventListener("click", closeModal);
document.getElementById("modalOverlay").addEventListener("click", e => { if (e.target === e.currentTarget) closeModal(); });
document.getElementById("subForm").addEventListener("submit", saveSub);
document.getElementById("btnDelete").addEventListener("click", deleteSub);
document.getElementById("filterCategory").addEventListener("change", e => { state.currentFilter.category = e.target.value; loadSubs(); });
document.getElementById("filterStatus").addEventListener("change", e => { state.currentFilter.status = e.target.value; loadSubs(); });

// CSV
document.getElementById("btnCsvImport").addEventListener("click", openCsvModal);
document.getElementById("csvModalClose").addEventListener("click", closeCsvModal);
document.getElementById("csvModalOverlay").addEventListener("click", e => { if (e.target === e.currentTarget) closeCsvModal(); });
const uploadZone = document.getElementById("uploadZone");
uploadZone.addEventListener("click", () => document.getElementById("csvFileInput").click());
uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("dragover"); });
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".csv")) handleCsvUpload(file);
});
document.getElementById("csvFileInput").addEventListener("change", e => {
    const file = e.target.files[0];
    if (file) handleCsvUpload(file);
});

// Email
document.getElementById("btnEmailScan").addEventListener("click", openEmailModal);
document.getElementById("emailModalClose").addEventListener("click", closeEmailModal);
document.getElementById("emailModalOverlay").addEventListener("click", e => { if (e.target === e.currentTarget) closeEmailModal(); });
document.getElementById("btnEmailCancel").addEventListener("click", closeEmailModal);
document.getElementById("btnEmailStart").addEventListener("click", startEmailScan);

// Scan modal
document.getElementById("scanModalClose").addEventListener("click", closeScanModal);
document.getElementById("scanModalOverlay").addEventListener("click", e => { if (e.target === e.currentTarget) closeScanModal(); });

// Smart text
document.getElementById("btnSmartParse").addEventListener("click", openSmartModal);
document.getElementById("smartModalClose").addEventListener("click", closeSmartModal);
document.getElementById("smartModalOverlay").addEventListener("click", e => { if (e.target === e.currentTarget) closeSmartModal(); });
document.getElementById("btnSmartCancel").addEventListener("click", closeSmartModal);
document.getElementById("btnSmartSubmit").addEventListener("click", submitSmartParse);
// SMS upload via smart modal
document.getElementById("btnSmsUpload").addEventListener("click", openSmartModal);
document.getElementById("btnSmsUploadTrigger").addEventListener("click", () => document.getElementById("smsFileInput").click());
document.getElementById("smsFileInput").addEventListener("change", e => {
    const file = e.target.files[0];
    if (file) handleSmsUpload(file);
});

// ---- Init ----
loadAll();
