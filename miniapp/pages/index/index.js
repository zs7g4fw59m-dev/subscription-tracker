const app = getApp();

const FX = { CNY: 1, USD: 7.2, EUR: 7.8, HKD: 0.92 };
const COLORS = {
  "AI工具": "#6366f1", "视频娱乐": "#f43f5e", "音乐": "#8b5cf6", "云存储": "#3b82f6",
  "阅读": "#10b981", "效率办公": "#f59e0b", "购物": "#f97316", "外卖生活": "#f97316",
  "社交社区": "#8b5cf6", "健身": "#14b8a6", "游戏": "#ec4899", "教育": "#14b8a6",
  "开发服务": "#6366f1", "App Store": "#3b82f6", "其他": "#64748b",
};
const ICONS = {
  "AI工具": "🤖", "视频娱乐": "📺", "音乐": "🎵", "云存储": "☁️", "阅读": "📖",
  "效率办公": "⚡", "购物": "🛒", "外卖生活": "🍱", "社交社区": "👥", "健身": "💪",
  "游戏": "🎮", "教育": "🎓", "开发服务": "🔧", "App Store": "🍎", "其他": "📌",
};
const CYCLE_OPTIONS = [
  { label: "月度", value: "monthly" }, { label: "年度", value: "yearly" },
  { label: "季度", value: "quarterly" }, { label: "每周", value: "weekly" },
  { label: "终身", value: "lifetime" },
];
const CYCLE_LABELS = { monthly: "月", yearly: "年", quarterly: "季", weekly: "周", lifetime: "永久" };
const STATUS_LABELS = { active: "活跃", paused: "暂停", cancelled: "取消" };
const SYMBOLS = { CNY: "¥", USD: "$", EUR: "€", HKD: "HK$" };

Page({
  data: {
    stats: {}, subs: [], filterCategory: "", filterStatus: "active",
    statusOptions: ["活跃", "暂停", "取消", "全部"],
    statusIndex: 0,
    statusValues: ["active", "paused", "cancelled", "all"],
    // Modal state
    modalVisible: false, editingId: null,
    currencyOptions: ["¥ CNY", "$ USD", "€ EUR", "HK$ HKD"],
    currencyValues: ["CNY", "USD", "EUR", "HKD"],
    cycleOptions: CYCLE_OPTIONS,
    form: {},
    // Smart parse
    smartVisible: false, smartText: "", smartLoading: false, smartError: "",
    detectedItems: [],
    // Toast
    toastMsg: "",
  },

  onLoad() { this.loadAll(); },
  onPullDownRefresh() { this.loadAll().then(() => wx.stopPullDownRefresh()); },

  // ---- API ----
  api(path, opts = {}) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: app.globalData.baseURL + path,
        method: opts.method || "GET",
        header: { "Content-Type": "application/json" },
        data: opts.body ? JSON.parse(opts.body) : undefined,
        success: res => res.statusCode < 400 ? resolve(res.data) : reject(new Error((res.data && res.data.error) || "请求失败")),
        fail: () => reject(new Error("网络错误")),
      });
    });
  },

  // ---- Data loading ----
  async loadAll() {
    try {
      const [stats, subs] = await Promise.all([
        this.api("/api/stats"),
        this.api("/api/subscriptions?category=" + this.data.filterCategory + "&status=" + this.data.filterStatus),
      ]);
      this.setData({
        stats,
        subs: this.decorateSubs(subs),
      });
    } catch (e) {
      this.toast("加载失败: " + e.message);
    }
  },

  decorateSubs(subs) {
    return subs.map(s => {
      const monthly = this.toMonthly(this.toCNY(s.amount, s.currency), s.cycle);
      return {
        ...s,
        _color: COLORS[s.category] || COLORS["其他"],
        _icon: ICONS[s.category] || "📌",
        _symbol: SYMBOLS[s.currency] || s.currency,
        _cycleLabel: CYCLE_LABELS[s.cycle] || s.cycle,
        _statusLabel: STATUS_LABELS[s.status] || s.status,
        _cnyMonthly: monthly,
      };
    });
  },

  // ---- Helpers ----
  toCNY(amount, currency) { return Math.round(amount * (FX[currency] || 1) * 100) / 100; },
  toMonthly(amount, cycle) {
    const rates = { monthly: 1, yearly: 1 / 12, quarterly: 1 / 3, weekly: 4.33, lifetime: 0 };
    return Math.round(amount * (rates[cycle] || 1) * 100) / 100;
  },
  toast(msg) { this.setData({ toastMsg: msg }); setTimeout(() => this.setData({ toastMsg: "" }), 2000); },

  // ---- Category filter ----
  toggleCategory(e) {
    const cat = e.currentTarget.dataset.cat;
    const next = this.data.filterCategory === cat ? "" : cat;
    this.setData({ filterCategory: next });
    this.loadAll();
  },

  onStatusChange(e) {
    const idx = parseInt(e.detail.value);
    this.setData({ statusIndex: idx, filterStatus: this.data.statusValues[idx] });
    this.loadAll();
  },

  // ---- Modal (add/edit) ----
  showAddModal() {
    this.setData({
      modalVisible: true, editingId: null,
      form: { name: "", amount: "", category: "", notes: "", next_renewal: "",
        _currencyIndex: 0, _cycleIndex: 0, _statusIndex: 0 },
    });
  },

  editSub(e) {
    const sub = this.data.subs.find(s => s.id === e.currentTarget.dataset.id);
    if (!sub) return;
    this.setData({
      modalVisible: true, editingId: sub.id,
      form: {
        name: sub.name, amount: String(sub.amount), category: sub.category || "",
        notes: sub.notes || "", next_renewal: sub.next_renewal || "",
        _currencyIndex: ["CNY", "USD", "EUR", "HKD"].indexOf(sub.currency),
        _cycleIndex: CYCLE_OPTIONS.findIndex(c => c.value === sub.cycle),
        _statusIndex: this.data.statusValues.indexOf(sub.status),
      },
    });
  },

  closeModal() { this.setData({ modalVisible: false }); },

  onFormInput(e) {
    const field = e.currentTarget.dataset.field;
    const form = { ...this.data.form, [field]: e.detail.value };
    this.setData({ form });
  },
  onCurrencyChange(e) {
    const form = { ...this.data.form, _currencyIndex: parseInt(e.detail.value) };
    this.setData({ form });
  },
  onCycleChange(e) {
    const form = { ...this.data.form, _cycleIndex: parseInt(e.detail.value) };
    this.setData({ form });
  },
  onDateChange(e) {
    const form = { ...this.data.form, next_renewal: e.detail.value };
    this.setData({ form });
  },
  onFormStatusChange(e) {
    const form = { ...this.data.form, _statusIndex: parseInt(e.detail.value) };
    this.setData({ form });
  },

  async saveSub() {
    const f = this.data.form;
    const body = {
      name: f.name || "未命名",
      amount: parseFloat(f.amount) || 0,
      currency: this.data.currencyValues[f._currencyIndex] || "CNY",
      cycle: CYCLE_OPTIONS[f._cycleIndex].value,
      category: f.category || "其他",
      next_renewal: f.next_renewal || null,
      status: this.data.statusValues[f._statusIndex] || "active",
      notes: f.notes || "",
    };

    try {
      if (this.data.editingId) {
        await this.api("/api/subscriptions/" + this.data.editingId, { method: "PUT", body: JSON.stringify(body) });
      } else {
        await this.api("/api/subscriptions", { method: "POST", body: JSON.stringify(body) });
      }
      this.closeModal();
      this.loadAll();
      this.toast("保存成功");
    } catch (e) {
      this.toast("保存失败: " + e.message);
    }
  },

  async deleteSub() {
    if (!this.data.editingId) return;
    try {
      await this.api("/api/subscriptions/" + this.data.editingId, { method: "DELETE" });
      this.closeModal();
      this.loadAll();
      this.toast("已删除");
    } catch (e) {
      this.toast("删除失败: " + e.message);
    }
  },

  // ---- Smart parse ----
  showSmartModal() { this.setData({ smartVisible: true, smartText: "", smartError: "", detectedItems: [] }); },
  closeSmartModal() { this.setData({ smartVisible: false }); },
  onSmartInput(e) { this.setData({ smartText: e.detail.value }); },

  async doSmartParse() {
    if (!this.data.smartText.trim()) { this.setData({ smartError: "请输入账单文字" }); return; }
    this.setData({ smartLoading: true, smartError: "" });
    try {
      const data = await this.api("/api/parse/text", { method: "POST", body: JSON.stringify({ text: this.data.smartText }) });
      const items = (data.subscriptions || []).map(s => ({
        ...s, _checked: true, _symbol: SYMBOLS[s.currency] || s.currency,
        _cycleLabel: CYCLE_LABELS[s.cycle] || s.cycle,
      }));
      this.setData({ detectedItems: items, smartLoading: false });
    } catch (e) {
      this.setData({ smartError: e.message, smartLoading: false });
    }
  },

  toggleCheck(e) {
    const idx = e.currentTarget.dataset.index;
    const items = [...this.data.detectedItems];
    items[idx]._checked = !items[idx]._checked;
    this.setData({ detectedItems: items });
  },

  async importDetected() {
    const items = this.data.detectedItems.filter(it => it._checked);
    if (!items.length) return;
    try {
      await this.api("/api/subscriptions/batch-import", { method: "POST", body: JSON.stringify({ items }) });
      this.closeSmartModal();
      this.loadAll();
      this.toast("已导入 " + items.length + " 笔");
    } catch (e) {
      this.toast("导入失败: " + e.message);
    }
  },

  // ---- SMS upload ----
  showSmsUpload() {
    wx.chooseMessageFile({
      count: 1,
      type: "file",
      extension: ["xml", "csv"],
      success: res => this.uploadSms(res.tempFiles[0].path),
    });
  },

  uploadSms(filePath) {
    wx.showLoading({ title: "解析中..." });
    wx.uploadFile({
      url: app.globalData.baseURL + "/api/import/sms",
      filePath: filePath,
      name: "file",
      success: res => {
        wx.hideLoading();
        try {
          const data = JSON.parse(res.data);
          if (res.statusCode >= 400) throw new Error(data.error || "解析失败");
          const items = (data.subscriptions || []).map(s => ({
            ...s, _checked: true, _symbol: SYMBOLS[s.currency] || s.currency,
            _cycleLabel: CYCLE_LABELS[s.cycle] || s.cycle,
          }));
          this.setData({ smartVisible: true, detectedItems: items });
        } catch (e) {
          this.toast(e.message);
        }
      },
      fail: () => { wx.hideLoading(); this.toast("上传失败"); },
    });
  },

  noop() {},
});
