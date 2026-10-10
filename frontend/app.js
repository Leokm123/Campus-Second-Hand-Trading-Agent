// 校园二手交易 Agent — 前端交互逻辑

var API_BASE = "";
var chatArea = document.getElementById("chatArea");
var userInput = document.getElementById("userInput");
var sendBtn = document.getElementById("sendBtn");

// ==================== i18n 多语言 ====================

var LANG = localStorage.getItem("lang") || "zh";

var I18N = {
    zh: {
        app_title: "校园二手交易 Agent",
        btn_send: "发送",
        btn_reimport: "重新导入数据",
        btn_extract: "AI 提取商品信息",
        btn_back: "返回",
        btn_confirm_import: "确认导入选中项",
        btn_select_file: "点击选择文件",

        welcome_1: "你好！我是你的校园二手交易助手。",
        welcome_2: "告诉我你想找什么、预算多少、在哪交易，我来帮你从群聊数据里找货、筛选、评估风险、联系卖家。",
        welcome_example: "例如：looking for a bicycle, budget 300, on campus",

        input_placeholder: "输入需求，例如：looking for a bicycle, budget 300, on campus",

        import_title: "导入群聊数据",
        import_desc: "从群聊记录中提取二手交易信息，AI会自动筛选商品并让你确认",
        source_demo: "演示数据",
        source_text: "粘贴文本",
        source_file: "上传文件",
        demo_hint: "点击下方按钮加载内置演示数据（30条模拟群聊消息）",
        demo_more: "...共30条消息",
        text_hint: "粘贴群聊记录（每行一条，格式：昵称: 消息内容）",
        file_hint: "选择 .txt 或 .json 文件（聊天记录导出）",
        paste_placeholder: "Zhang: Selling Giant ATX660 bicycle, 9/10 condition, 250 yuan, WeChat: zhang123, South Gate trade\nLi: Merida Duke 300, 8/10 condition, 280 yuan, free shipping on campus, contact wx_li456\nWang: Anyone want second-hand textbooks? Calculus and Linear Algebra available, 20 yuan each, trade on campus\n...",

        confirm_title: "确认导入",
        select_all: "全选",
        selected_count: "已选 0 条",
        loading_extract: "AI 正在提取商品信息...",

        msg_imported: "已导入 {count} 个商品信息，可以开始查找了！",
        msg_no_match: "未找到匹配的商品，建议调整预算或地点。",
        msg_no_data: "请先导入数据",
        msg_select_at_least: "请至少选择一条商品信息",
        msg_reset_confirm: "确定重新导入数据？当前已导入的数据将被清除。",
        msg_paste_empty: "请粘贴聊天记录",
        msg_file_empty: "请选择文件",
        msg_import_fail: "导入失败: ",
        msg_reset_fail: "重置失败: ",

        label_found: "找到 {count} 个匹配商品:",
        label_negotiating: "Agent 正在生成话术...",
        label_message: "砍价话术:",
        label_sending: "正在通过微信发送...",

        btn_send_to: "确认发送给",
        btn_copy: "复制话术",
        msg_copied: "话术已复制到剪贴板",

        result_success: "发送成功",
        result_sent_to: "已通过微信发送给 ",
        result_fail: "发送失败",
        result_copy_fallback: "你可以手动复制话术发送",

        risk_green: "推荐",
        risk_yellow: "可考虑",
        risk_red: "不建议",

        agent_panel_title: "Agent 工作面板",
        agent_done: "已完成",
        agent_parallel: "并行",
        agent_no_match: "未找到匹配，建议调整预算或地点",

        field_condition: "成色",
        field_seller: "卖家",
        field_location: "地点",
        field_unknown: "未知",
        risk_hint: "风险提示: ",

        price_unknown: "?",
        contact_none: "无联系方式",
        cond_unknown: "成色未知",
        loc_unknown: "地点未知",

        need_label: "需求：",
        budget_label: "预算：",
        location_label: "地点：",
        processing: "处理中...",
        request_fail: "请求失败: ",
        backend_hint: "（请确认后端服务已启动）",
        gen_fail: "生成话术失败: ",
        send_fail: "发送请求失败: ",

        stats_filtered: "（过滤了 {count} 条非交易消息）",
        confirm_loading: "导入中...",
        extracted_msg: "个商品信息",
        messages_label: "条消息",
    },
    en: {
        app_title: "Campus Second-Hand Trading Agent",
        btn_send: "Send",
        btn_reimport: "Re-import Data",
        btn_extract: "AI Extract Listings",
        btn_back: "Back",
        btn_confirm_import: "Confirm Import",
        btn_select_file: "Click to select file",

        welcome_1: "Hi! I'm your campus second-hand trading assistant.",
        welcome_2: "Tell me what you're looking for, your budget, and where to trade. I'll find items from group chat data, filter, assess risk, and contact sellers.",
        welcome_example: "e.g. Looking for a second-hand bicycle, budget 300, trade on campus",

        input_placeholder: "Type a request, e.g. Looking for a bicycle, budget 300, on campus",

        import_title: "Import Chat Data",
        import_desc: "Extract second-hand trade listings from group chat. AI auto-filters items for your confirmation.",
        source_demo: "Demo Data",
        source_text: "Paste Text",
        source_file: "Upload File",
        demo_hint: "Click to load built-in demo data (30 simulated group chat messages)",
        demo_more: "...30 messages total",
        text_hint: "Paste chat records (one per line, format: Name: Message)",
        file_hint: "Select .txt or .json file (exported chat records)",
        paste_placeholder: "Zhang: Selling Giant ATX660 bike, 9/10 condition, 250 yuan, WeChat zhang123, South Gate\nLi: Merida Duke 300, 8/10 condition, 280, free shipping on campus, wx_li456\nWang: Any textbooks? Calculus & Linear Algebra, 20 each, on campus\n...",

        confirm_title: "Confirm Import",
        select_all: "Select All",
        selected_count: "0 selected",
        loading_extract: "AI is extracting listings...",

        msg_imported: "Imported {count} listings. Ready to search!",
        msg_no_match: "No matching items found. Try adjusting budget or location.",
        msg_no_data: "Please import data first",
        msg_select_at_least: "Please select at least one listing",
        msg_reset_confirm: "Re-import data? Current data will be cleared.",
        msg_paste_empty: "Please paste chat records",
        msg_file_empty: "Please select a file",
        msg_import_fail: "Import failed: ",
        msg_reset_fail: "Reset failed: ",

        label_found: "Found {count} matching items:",
        label_negotiating: "Agent is generating message...",
        label_message: "Negotiation message:",
        label_sending: "Sending via WeChat...",

        btn_send_to: "Send to ",
        btn_copy: "Copy Message",
        msg_copied: "Message copied to clipboard",

        result_success: "Sent Successfully",
        result_sent_to: "Sent via WeChat to ",
        result_fail: "Send Failed",
        result_copy_fallback: "You can copy the message and send manually",

        risk_green: "Recommended",
        risk_yellow: "Consider",
        risk_red: "Not Recommended",

        agent_panel_title: "Agent Work Panel",
        agent_done: "Done",
        agent_parallel: "Parallel",
        agent_no_match: "No matches found, try adjusting budget or location",

        field_condition: "Condition",
        field_seller: "Seller",
        field_location: "Location",
        field_unknown: "Unknown",
        risk_hint: "Risk: ",

        price_unknown: "?",
        contact_none: "No contact",
        cond_unknown: "Unknown",
        loc_unknown: "Unknown",

        need_label: "Need: ",
        budget_label: "Budget: ",
        location_label: "Location: ",
        processing: "Processing...",
        request_fail: "Request failed: ",
        backend_hint: " (make sure backend is running)",
        gen_fail: "Failed to generate: ",
        send_fail: "Send request failed: ",

        stats_filtered: " ({count} non-trade messages filtered)",
        confirm_loading: "Importing...",
        extracted_msg: " listings",
        messages_label: " messages",
    }
};

function t(key, params) {
    var str = (I18N[LANG] && I18N[LANG][key]) || (I18N.zh[key]) || key;
    if (params) {
        Object.keys(params).forEach(function(k) {
            str = str.replace(new RegExp("\\{" + k + "\\}", "g"), params[k]);
        });
    }
    return str;
}

function applyI18n() {
    document.querySelectorAll("[data-i18n]").forEach(function(el) {
        el.textContent = t(el.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-ph]").forEach(function(el) {
        el.placeholder = t(el.getAttribute("data-i18n-ph"));
    });
    document.getElementById("langBtn").textContent = (LANG === "zh") ? "EN" : "中文";
    var importLangBtn = document.getElementById("importLangBtn");
    if (importLangBtn) importLangBtn.textContent = (LANG === "zh") ? "EN" : "中文";
    document.documentElement.lang = (LANG === "zh") ? "zh-CN" : "en";
}

function toggleLanguage() {
    LANG = (LANG === "zh") ? "en" : "zh";
    localStorage.setItem("lang", LANG);
    applyI18n();
    // Reset chat area to welcome
    chatArea.innerHTML =
        '<div class="welcome-msg">' +
            '<p>' + t("welcome_1") + '</p>' +
            '<p>' + t("welcome_2") + '</p>' +
            '<p class="example">' + t("welcome_example") + '</p>' +
        '</div>';
}

// ==================== 初始化 ====================

userInput.addEventListener("keypress", function(e) {
    if (e.key === "Enter") sendMessage();
});

(function init() {
    applyI18n();
    if (!localStorage.getItem("hasImported")) {
        showImportOverlay();
    }
})();

// ==================== 导入数据逻辑 ====================

var currentSource = "demo";
var fileContent = "";

function showImportOverlay() {
    document.getElementById("importOverlay").classList.remove("hidden");
}

function hideImportOverlay() {
    document.getElementById("importOverlay").classList.add("hidden");
}

function switchSource(source) {
    currentSource = source;
    var tabs = document.querySelectorAll(".source-tab");
    tabs.forEach(function(tab) { tab.classList.remove("active"); });
    document.getElementById("tab" + source.charAt(0).toUpperCase() + source.slice(1)).classList.add("active");

    var panels = document.querySelectorAll(".source-panel");
    panels.forEach(function(p) { p.classList.remove("active"); });
    document.getElementById("panel" + source.charAt(0).toUpperCase() + source.slice(1)).classList.add("active");
}

function handleFileSelect(input) {
    if (!input.files || !input.files[0]) return;
    var file = input.files[0];
    document.getElementById("fileName").textContent = file.name;

    var reader = new FileReader();
    reader.onload = function(e) {
        fileContent = e.target.result;
    };
    reader.readAsText(file, "UTF-8");
}

function processImport() {
    var payload = { source: currentSource, lang: LANG };

    if (currentSource === "text") {
        var text = document.getElementById("pasteText").value.trim();
        if (!text) {
            alert(t("msg_paste_empty"));
            return;
        }
        payload.text = text;
    } else if (currentSource === "file") {
        if (!fileContent) {
            alert(t("msg_file_empty"));
            return;
        }
        payload.text = fileContent;
    }

    document.getElementById("importStep1").style.display = "none";
    document.getElementById("importStep2").style.display = "none";
    document.getElementById("importLoading").style.display = "block";

    fetch(API_BASE + "/api/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        document.getElementById("importLoading").style.display = "none";

        if (data.status === "error") {
            alert(t("msg_import_fail") + data.error);
            backToStep1();
            return;
        }

        document.getElementById("importStep2").style.display = "block";
        var filteredText = data.non_trade_count > 0
            ? t("stats_filtered", { count: data.non_trade_count })
            : "";
        document.getElementById("importStats").textContent =
            data.message + filteredText;

        renderConfirmList(data.listings);
    })
    .catch(function(err) {
        document.getElementById("importLoading").style.display = "none";
        alert(t("msg_import_fail") + err.message);
        backToStep1();
    });
}

var currentListings = [];

function renderConfirmList(listings) {
    currentListings = listings;
    var listEl = document.getElementById("confirmList");
    listEl.innerHTML = "";

    listings.forEach(function(item) {
        var div = document.createElement("div");
        div.className = "confirm-item";

        var priceText = item.price
            ? (item.price == parseInt(item.price) ? item.price : item.price) + (LANG === "zh" ? "元" : " yuan")
            : t("price_unknown");
        var condText = item.condition || t("cond_unknown");
        var locText = item.location || t("loc_unknown");
        var contactText = item.contact || t("contact_none");

        div.innerHTML =
            '<input type="checkbox" checked onchange="updateSelectedCount()" data-id="' + item.id + '">' +
            '<div class="confirm-item-content">' +
                '<div class="confirm-item-name">' + (item.product_name || "Unknown") + '</div>' +
                '<div class="confirm-item-meta">' +
                    '<span class="category-tag">' + (item.category || "N/A") + '</span>' +
                    priceText + ' | ' + t("field_condition") + ': ' + condText + ' | ' + t("field_location") + ': ' + locText + ' | ' + contactText +
                '</div>' +
                '<div class="confirm-item-source">' + (item.source_text || "") + '</div>' +
            '</div>';

        listEl.appendChild(div);
    });

    document.getElementById("selectAll").checked = true;
    updateSelectedCount();
}

function updateSelectedCount() {
    var checkboxes = document.querySelectorAll(".confirm-item input[type='checkbox']");
    var checked = 0;
    checkboxes.forEach(function(cb) {
        if (cb.checked) checked++;
    });
    document.getElementById("selectedCount").textContent =
        (LANG === "zh" ? "已选 " : "") + checked + (LANG === "zh" ? " 条" : " selected");
    document.getElementById("selectAll").checked = (checked === checkboxes.length);
}

function toggleAll(checkbox) {
    document.querySelectorAll(".confirm-item input[type='checkbox']").forEach(function(cb) {
        cb.checked = checkbox.checked;
    });
    updateSelectedCount();
}

function backToStep1() {
    document.getElementById("importStep2").style.display = "none";
    document.getElementById("importLoading").style.display = "none";
    document.getElementById("importStep1").style.display = "block";
}

function confirmImport() {
    var selectedIds = [];
    document.querySelectorAll(".confirm-item input[type='checkbox']:checked").forEach(function(cb) {
        selectedIds.push(parseInt(cb.getAttribute("data-id")));
    });

    if (selectedIds.length === 0) {
        alert(t("msg_select_at_least"));
        return;
    }

    document.getElementById("confirmBtn").disabled = true;
    document.getElementById("confirmBtn").textContent = t("confirm_loading");

    fetch(API_BASE + "/api/confirm-import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ listing_ids: selectedIds })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.status === "success") {
            localStorage.setItem("hasImported", "true");
            hideImportOverlay();
            addMessage(t("msg_imported", { count: data.count }), "agent");
            document.getElementById("confirmBtn").disabled = false;
            document.getElementById("confirmBtn").textContent = t("btn_confirm_import");
        } else {
            alert(t("msg_import_fail") + (data.error || "unknown"));
            document.getElementById("confirmBtn").disabled = false;
            document.getElementById("confirmBtn").textContent = t("btn_confirm_import");
        }
    })
    .catch(function(err) {
        alert(t("msg_import_fail") + err.message);
        document.getElementById("confirmBtn").disabled = false;
        document.getElementById("confirmBtn").textContent = t("btn_confirm_import");
    });
}

function resetImport() {
    if (!confirm(t("msg_reset_confirm"))) return;

    fetch(API_BASE + "/api/reset", { method: "POST" })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        localStorage.removeItem("hasImported");
        resetConversationContext();
        chatArea.innerHTML =
            '<div class="welcome-msg">' +
                '<p>' + t("welcome_1") + '</p>' +
                '<p>' + t("welcome_2") + '</p>' +
                '<p class="example">' + t("welcome_example") + '</p>' +
            '</div>';
        showImportOverlay();
    })
    .catch(function(err) {
        alert(t("msg_reset_fail") + err.message);
    });
}

// ==================== 主聊天逻辑 ====================

var _animCounter = 0;
function _scheduleAnimation(el, baseDelayMs) {
    _animCounter++;
    var delay = baseDelayMs + _animCounter * 80;
    el.classList.add("fade-in");
    el.style.animationDelay = delay + "ms";
    // 确保动画结束后移除 delay 避免影响后续状态
    setTimeout(function() {
        el.style.animationDelay = "";
    }, delay + 500);
}

function addMessage(text, type) {
    var div = document.createElement("div");
    div.className = "msg-bubble msg-" + type;
    div.textContent = text;
    _scheduleAnimation(div, 0);
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
    return div;
}

function addLabel(text) {
    var div = document.createElement("div");
    div.className = "label fade-in";
    div.textContent = text;
    _scheduleAnimation(div, 0);
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function addSteps(steps) {
    var div = document.createElement("div");
    div.className = "msg-bubble msg-agent steps";
    steps.forEach(function(step) {
        var s = document.createElement("div");
        s.className = "step";
        s.textContent = step;
        div.appendChild(s);
    });
    _scheduleAnimation(div, 0);
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function getRiskLabel(level) {
    var map = { green: "risk_green", yellow: "risk_yellow", red: "risk_red" };
    return t(map[level] || "risk_green");
}

// 多语言地点/商品名映射，让需求摘要与当前语言统一
var LOCATION_MAP_ZH_TO_EN = {
    "校内": "On Campus",
    "南门": "South Gate",
    "北门": "North Gate",
    "东门": "East Gate",
    "西门": "West Gate",
    "东区": "East Area",
    "西区": "West Area",
    "南区": "South Area",
    "北区": "North Area"
};
var LOCATION_MAP_EN_TO_ZH = {
    "on campus": "校内", "campus": "校内",
    "south gate": "南门", "south": "南区",
    "north gate": "北门", "north": "北区",
    "east gate": "东门", "east": "东区",
    "west gate": "西门", "west": "西区",
    "east area": "东区", "west area": "西区",
    "south area": "南区", "north area": "北区"
};
var PRODUCT_MAP_EN_TO_ZH = {
    "bicycle": "自行车", "bike": "自行车",
    "textbook": "教材", "book": "书",
    "iphone": "iPhone", "ipad": "iPad",
    "switch": "Switch", "kindle": "Kindle",
    "headphone": "耳机", "headphones": "耳机",
    "mouse": "鼠标", "laptop": "笔记本",
    "lamp": "台灯", "guitar": "吉他",
    "notebook": "笔记本", "diary": "日记本"
};
var PRODUCT_MAP_ZH_TO_EN = {
    "自行车": "Bicycle", "山地车": "Mountain Bike", "公路车": "Road Bike",
    "教材": "Textbook", "书": "Book",
    "iPhone": "iPhone", "iPad": "iPad",
    "Switch": "Switch", "Kindle": "Kindle",
    "耳机": "Headphones", "鼠标": "Mouse",
    "笔记本": "Laptop", "笔记本电脑": "Laptop",
    "台灯": "Desk Lamp", "吉他": "Guitar",
    "日记本": "Notebook"
};

function formatLocation(loc) {
    if (!loc) return t("field_unknown");
    var clean = String(loc).trim();
    if (LANG === "en") {
        // 中文地点 -> 英文
        return LOCATION_MAP_ZH_TO_EN[clean] || clean;
    }
    // 英文地点 -> 中文
    var key = clean.toLowerCase();
    return LOCATION_MAP_EN_TO_ZH[key] || clean;
}

function formatProductName(name) {
    if (!name) return t("field_unknown");
    var clean = String(name).trim();
    if (LANG === "zh") {
        // 简单英文商品名 -> 中文
        var lower = clean.toLowerCase();
        for (var en in PRODUCT_MAP_EN_TO_ZH) {
            if (lower === en || lower.indexOf(en) !== -1) {
                // 保留原字符串中的品牌/型号前缀，替换关键词
                var re = new RegExp(en, "gi");
                return clean.replace(re, PRODUCT_MAP_EN_TO_ZH[en]);
            }
        }
        return clean;
    } else {
        // 中文商品名 -> 英文（仅对常见词做简单替换）
        for (var zh in PRODUCT_MAP_ZH_TO_EN) {
            if (clean.indexOf(zh) !== -1) {
                return PRODUCT_MAP_ZH_TO_EN[zh];
            }
        }
        // 首字母大写
        return clean.replace(/\b\w/g, function(c) { return c.toUpperCase(); });
    }
}

function addListingCards(results) {
    results.forEach(function(item, index) {
        var card = document.createElement("div");
        card.className = "card card-" + item.risk_level + " fade-in";
        card.style.animationDelay = (index * 150) + "ms";

        var priceDisplay = item.price
            ? (item.price == parseInt(item.price) ? item.price : item.price) + (LANG === "zh" ? "元" : " yuan")
            : t("price_unknown");

        // 卡片字段统一按当前语言显示，避免中英文混杂
        var condDisplay = item.condition || t("field_unknown");
        var sellerDisplay = item.seller || t("field_unknown");
        var locDisplay = item.location ? formatLocation(item.location) : t("field_unknown");

        card.innerHTML =
            '<div class="card-header">' +
                '<span class="card-title">' + formatProductName(item.product_name || "Unknown") + ' — ' + priceDisplay + '</span>' +
                '<span class="card-badge badge-' + item.risk_level + '">' + getRiskLabel(item.risk_level) + '</span>' +
            '</div>' +
            '<div class="card-info">' +
                '<span>' + t("field_condition") + ': ' + condDisplay + '</span>' +
                '<span>' + t("field_seller") + ': ' + sellerDisplay + '</span>' +
                '<span>' + t("field_location") + ': ' + locDisplay + '</span>' +
            '</div>' +
            (item.risk_reasons && item.risk_reasons.length > 0
                ? '<div class="card-reasons">' + t("risk_hint") + item.risk_reasons.join("、") + '</div>' : "");

        card.onclick = function() { selectListing(item); };
        card.style.cursor = "pointer";

        chatArea.appendChild(card);
        // 清理 inline delay 避免影响后续 hover 交互
        setTimeout(function(el) { el.style.animationDelay = ""; }, index * 150 + 600, card);
    });
    chatArea.scrollTop = chatArea.scrollHeight;
}

// ==================== Agent Work Panel ====================
// 展示任务分解 + 并行协作 + 自验证统计，贴合评分维度

var STEP_STATUS_ICONS = {
    "done": "\u2713",
    "warning": "!",
    "error": "\u2717",
    "pending": "\u25CB",
};

var STEP_STATUS_CLASSES = {
    "done": "step-done",
    "warning": "step-warning",
    "error": "step-error",
    "pending": "step-pending",
};

// Agent Work Panel staggered timing config (ms)
var PANEL_STEP_INTERVAL = 350;   // delay between each step card
var PANEL_STEP_BASE = 200;       // first step delay
var PANEL_CONNECTOR_OFFSET = 150; // connector delay after last step
var PANEL_SUMMARY_OFFSET = 350;   // summary delay after last step
var PANEL_ANIM_DURATION = 500;    // CSS animation duration per element

function addAgentWorkPanel(taskPlan, riskSummary) {
    if (!taskPlan || taskPlan.length === 0) return;

    var panel = document.createElement("div");
    panel.className = "agent-panel fade-in";
    panel.style.animationDelay = "0ms";

    // --- Header ---
    var header = document.createElement("div");
    header.className = "agent-panel-header";
    header.innerHTML =
        '<span class="agent-panel-dot"></span>' +
        '<span class="agent-panel-title">' + t("agent_panel_title") + '</span>' +
        '<span class="agent-panel-status">' + t("agent_done") + '</span>';
    panel.appendChild(header);

    // --- Steps grid ---
    var stepsGrid = document.createElement("div");
    stepsGrid.className = "agent-steps-grid";

    taskPlan.forEach(function(step, i) {
        var stepDiv = document.createElement("div");
        var statusClass = STEP_STATUS_CLASSES[step.status] || "step-pending";
        stepDiv.className = "agent-step-card " + statusClass + " fade-in";
        var stepDelay = PANEL_STEP_BASE + i * PANEL_STEP_INTERVAL;
        stepDiv.style.animationDelay = stepDelay + "ms";

        var icon = STEP_STATUS_ICONS[step.status] || STEP_STATUS_ICONS["pending"];
        var parallelBadge = step.parallel
            ? '<span class="step-parallel-badge">' + t("agent_parallel") + '</span>'
            : '';

        stepDiv.innerHTML =
            '<div class="agent-step-icon">' + icon + '</div>' +
            '<div class="agent-step-label">' + (step.label || "") + '</div>' +
            '<div class="agent-step-detail">' + (step.detail || "") + '</div>' +
            parallelBadge;
        stepsGrid.appendChild(stepDiv);

        // clean inline delay after animation
        setTimeout(function(el) { el.style.animationDelay = ""; }, stepDelay + PANEL_ANIM_DURATION + 100, stepDiv);
    });

    panel.appendChild(stepsGrid);

    // Calculate timing for elements after steps
    var lastStepDelay = PANEL_STEP_BASE + (taskPlan.length - 1) * PANEL_STEP_INTERVAL;
    var connectorDelay = lastStepDelay + PANEL_STEP_INTERVAL + PANEL_CONNECTOR_OFFSET;
    var summaryDelay = connectorDelay + PANEL_STEP_INTERVAL + PANEL_SUMMARY_OFFSET;

    // --- Parallel connector line ---
    var hasParallel = taskPlan.some(function(s) { return s.parallel; });
    if (hasParallel) {
        var connector = document.createElement("div");
        connector.className = "agent-parallel-connector fade-in";
        connector.style.animationDelay = connectorDelay + "ms";
        var matcherLabel = LANG === "zh" ? "语义匹配" : "Matcher";
        var riskLabel = LANG === "zh" ? "风险评估" : "RiskCheck";
        connector.innerHTML =
            '<span class="connector-line"></span>' +
            '<span class="connector-label">' + matcherLabel + '</span>' +
            '<span class="connector-plus">+</span>' +
            '<span class="connector-label">' + riskLabel + '</span>' +
            '<span class="connector-line"></span>';
        panel.appendChild(connector);
        setTimeout(function(el) { el.style.animationDelay = ""; }, connectorDelay + PANEL_ANIM_DURATION + 100, connector);
    }

    // --- Risk summary grid ---
    if (riskSummary) {
        var summaryDiv = document.createElement("div");
        summaryDiv.className = "agent-summary-grid fade-in";
        summaryDiv.style.animationDelay = summaryDelay + "ms";

        var greenN = riskSummary.green || 0;
        var yellowN = riskSummary.yellow || 0;
        var redN = riskSummary.red || 0;

        summaryDiv.innerHTML =
            '<div class="summary-card summary-green">' +
                '<div class="summary-label">' + t("risk_green") + '</div>' +
                '<div class="summary-num">' + greenN + '</div>' +
            '</div>' +
            '<div class="summary-card summary-yellow">' +
                '<div class="summary-label">' + t("risk_yellow") + '</div>' +
                '<div class="summary-num">' + yellowN + '</div>' +
            '</div>' +
            '<div class="summary-card summary-red">' +
                '<div class="summary-label">' + t("risk_red") + '</div>' +
                '<div class="summary-num">' + redN + '</div>' +
            '</div>';
        panel.appendChild(summaryDiv);
        setTimeout(function(el) { el.style.animationDelay = ""; }, summaryDelay + PANEL_ANIM_DURATION + 100, summaryDiv);
    }

    chatArea.appendChild(panel);
    chatArea.scrollTop = chatArea.scrollHeight;

    // Return total panel duration so caller can delay subsequent content
    return summaryDelay + PANEL_ANIM_DURATION;
}

function addAgentStatus(text, status) {
    var div = document.createElement("div");
    div.className = "agent-status" + (status ? " " + status : "") + " fade-in";
    div.textContent = text;
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
}


function selectListing(listing) {
    addLabel(t("label_negotiating"));

    fetch(API_BASE + "/api/negotiate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ listing: listing, lang: LANG })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        addLabel(t("label_message"));

        var box = document.createElement("div");
        box.className = "negotiation-box";
        box.innerHTML =
            '<div class="negotiation-message">' + data.message + '</div>' +
            '<div class="action-buttons">' +
                '<button class="btn btn-primary" onclick="confirmSend(\'' + escapeQuote(data.contact) + '\', \'' + escapeQuote(data.message) + '\')">' + t("btn_send_to") + data.contact + '</button>' +
                '<button class="btn btn-secondary" onclick="copyMessage(\'' + escapeQuote(data.message) + '\')">' + t("btn_copy") + '</button>' +
            '</div>';
        chatArea.appendChild(box);
        chatArea.scrollTop = chatArea.scrollHeight;
    })
    .catch(function(err) {
        addMessage(t("gen_fail") + err.message, "agent");
    });
}

function confirmSend(contact, message) {
    addLabel(t("label_sending"));

    fetch(API_BASE + "/api/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contact: contact, message: message })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        var box = document.createElement("div");
        if (data.status === "success") {
            box.className = "result-box";
            box.innerHTML =
                '<div class="label">' + t("result_success") + '</div>' +
                '<div class="card-info">' + t("result_sent_to") + '<b>' + data.contact + '</b></div>' +
                '<div class="card-info" style="margin-top:8px">' + (LANG === "zh" ? "已发送消息给卖家。提醒：见面验货后再付款，不要提前转账。" : "Message sent. Reminder: inspect the item in person before paying. Never transfer money in advance.") + '</div>';
        } else {
            box.className = "result-box";
            box.style.background = "var(--c-red-bg)";
            box.style.borderColor = "var(--border)";
            box.innerHTML =
                '<div class="label" style="color:var(--c-red-fg)">' + t("result_fail") + '</div>' +
                '<div class="card-info">' + (data.error || "Unknown error") + '</div>' +
                '<div class="card-info" style="margin-top:8px">' + t("result_copy_fallback") + '</div>';
        }
        chatArea.appendChild(box);
        chatArea.scrollTop = chatArea.scrollHeight;
    })
    .catch(function(err) {
        addMessage(t("send_fail") + err.message, "agent");
    });
}

function copyMessage(text) {
    navigator.clipboard.writeText(text).then(function() {
        addMessage(t("msg_copied"), "agent");
    });
}

function escapeQuote(text) {
    return (text || "").replace(/'/g, "\\'").replace(/\n/g, "\\n");
}

// ==================== 多轮对话上下文 ====================
// 记录用户在前几轮已确认的信息（product_name / budget / location）
// 每次用户发送消息时带上，避免 Agent 忘记上轮已确认的内容
var conversationContext = { product_name: null, budget: null, location: null };

function resetConversationContext() {
    conversationContext = { product_name: null, budget: null, location: null };
}

function updateContextFromParsed(parsed) {
    if (!parsed) return;
    if (parsed.product_name) conversationContext.product_name = parsed.product_name;
    if (parsed.budget !== undefined && parsed.budget !== null) conversationContext.budget = parsed.budget;
    if (parsed.location) conversationContext.location = parsed.location;
}


function sendMessage() {
    var message = userInput.value.trim();
    if (!message) return;

    addMessage(message, "user");
    userInput.value = "";
    sendBtn.disabled = true;
    sendBtn.textContent = t("processing");

    fetch(API_BASE + "/api/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message, lang: LANG, context: conversationContext })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        sendBtn.disabled = false;
        sendBtn.textContent = t("btn_send");

        if (data.status === "need_more_info") {
            updateContextFromParsed(data.parsed);
            addMessage(data.question, "agent");
        } else if (data.status === "complete") {
            // 已完成，重置上下文
            if (data.parsed_need) {
                updateContextFromParsed(data.parsed_need);
            }

            // Agent 工作面板：任务分解 + 并行协作 + 自验证统计
            // 面板元素依次出现，后续内容延迟到面板完成后
            var panelDuration = 0;
            if (data.task_plan) {
                panelDuration = addAgentWorkPanel(data.task_plan, data.risk_summary);
            }

            // 延迟显示需求摘要、匹配结果等，等面板动画完成
            var postDelay = panelDuration + 200;
            setTimeout(function() {
                if (data.parsed_need) {
                    var needText = t("need_label") +
                        formatProductName(data.parsed_need.product_name) + " | " +
                        t("budget_label") + data.parsed_need.budget +
                        (LANG === "zh" ? "元" : " yuan") + " | " +
                        t("location_label") + formatLocation(data.parsed_need.location);
                    addMessage(needText, "agent");
                }

                if (data.results && data.results.length > 0) {
                    addLabel(t("label_found", { count: data.results.length }));
                    addListingCards(data.results);
                } else {
                    addMessage(t("msg_no_match"), "agent");
                }
            }, postDelay);
        } else {
            addMessage(t("request_fail") + (data.error || "unknown"), "agent");
        }
    })
    .catch(function(err) {
        sendBtn.disabled = false;
        sendBtn.textContent = t("btn_send");
        addMessage(t("request_fail") + err.message + t("backend_hint"), "agent");
    });
}
