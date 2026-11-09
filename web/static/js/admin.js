/* Meike Tech · consultation admin console. */
(function () {
  "use strict";

  var TOKEN_KEY = "meike_admin_token";
  var state = {
    token: "",
    conversations: [],
    active: "",
    detail: null,
    lastMessageId: 0,
    search: "",
    timer: null,
    loggingOut: false
  };

  var $ = function (selector, scope) {
    return (scope || document).querySelector(selector);
  };
  var $$ = function (selector, scope) {
    return Array.prototype.slice.call((scope || document).querySelectorAll(selector));
  };

  function readToken() {
    try {
      return window.sessionStorage.getItem(TOKEN_KEY) || "";
    } catch (error) {
      return "";
    }
  }

  function saveToken(value) {
    try {
      if (value) window.sessionStorage.setItem(TOKEN_KEY, value);
      else window.sessionStorage.removeItem(TOKEN_KEY);
    } catch (error) {
      /* ignore */
    }
  }

  function toast(message) {
    var node = $("#admin-toast");
    if (!node) return;
    node.textContent = message;
    node.classList.add("show");
    window.clearTimeout(toast.timer);
    toast.timer = window.setTimeout(function () {
      node.classList.remove("show");
    }, 2800);
  }

  function setConn(ok) {
    var node = $("#conn-status");
    if (!node) return;
    node.classList.toggle("error", !ok);
    node.innerHTML = "";
    var dot = document.createElement("i");
    node.appendChild(dot);
    node.appendChild(document.createTextNode(ok ? " 已连接 · 自动刷新" : " 连接异常，正在重试"));
  }

  function api(path, options) {
    options = options || {};
    var headers = { "Content-Type": "application/json" };
    if (options.auth !== false && state.token) {
      headers["X-Admin-Token"] = state.token;
    }
    return fetch(path, {
      method: options.method || "GET",
      headers: headers,
      body: options.body,
      cache: "no-store",
      credentials: "same-origin"
    }).then(function (response) {
      return response
        .json()
        .catch(function () {
          return null;
        })
        .then(function (data) {
          if (response.status === 401) {
            logout("登录已过期，请重新登录");
            var authError = new Error("登录已过期");
            authError.status = 401;
            throw authError;
          }
          if (!response.ok) {
            var detail = data && data.detail;
            var error = new Error(
              typeof detail === "string" ? detail : "网络开小差了，请稍后再试"
            );
            error.status = response.status;
            throw error;
          }
          return data;
        });
    });
  }

  /* ------------------------------------------------------------------ auth */

  function showLogin() {
    $("#app-view").hidden = true;
    $("#login-view").hidden = false;
    var password = $("#password");
    if (password) {
      password.value = "";
      window.setTimeout(function () {
        password.focus();
      }, 80);
    }
  }

  function showApp() {
    $("#login-view").hidden = true;
    $("#app-view").hidden = false;
    startPolling();
  }

  function logout(message) {
    if (state.loggingOut) return;
    state.loggingOut = true;
    state.token = "";
    state.active = "";
    state.detail = null;
    state.conversations = [];
    saveToken("");
    stopPolling();
    showLogin();
    state.loggingOut = false;
    if (message) toast(message);
  }

  function verifyToken() {
    if (!state.token) {
      showLogin();
      return;
    }
    api("/api/admin/me")
      .then(function () {
        showApp();
        loadAll();
      })
      .catch(function (error) {
        if (error.status !== 401) {
          showLogin();
          toast("无法连接服务器，请检查网络");
        }
      });
  }

  function login(event) {
    event.preventDefault();
    var password = $("#password").value;
    if (!password) {
      toast("请输入管理密码");
      return;
    }
    var button = $("#login-btn");
    button.disabled = true;
    button.textContent = "登录中…";
    api("/api/admin/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ password: password })
    })
      .then(function (data) {
        state.token = data.token;
        saveToken(state.token);
        button.textContent = "进入后台";
        button.disabled = false;
        showApp();
        loadAll();
        toast("欢迎回来");
      })
      .catch(function (error) {
        button.disabled = false;
        button.textContent = "进入后台";
        toast(error.message || "登录失败");
        $("#password").select();
      });
  }

  /* -------------------------------------------------------------- overview */

  function loadOverview() {
    return api("/api/admin/overview")
      .then(function (data) {
        setConn(true);
        $("#stat-today").textContent = formatNumber(data.today);
        $("#stat-total").textContent = formatNumber(data.total);
        $("#stat-leads").textContent = formatNumber(data.leads);
        $("#stat-unread").textContent = formatNumber(data.unread);
      })
      .catch(function (error) {
        if (error.status !== 401) setConn(false);
      });
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString("zh-CN");
  }

  /* ----------------------------------------------------------- conversation */

  function loadConversations(silent) {
    var query = state.search ? "?q=" + encodeURIComponent(state.search) : "";
    return api("/api/admin/conversations" + query)
      .then(function (data) {
        setConn(true);
        var items = data.items || [];
        var signature = items
          .map(function (item) {
            return item.session_id + ":" + item.updated_at + ":" + item.unread_admin;
          })
          .join("|");
        state.conversations = items;
        if (!silent || signature !== loadConversations.signature) {
          loadConversations.signature = signature;
          renderList();
        }
      })
      .catch(function (error) {
        if (error.status !== 401) setConn(false);
      });
  }

  function renderList() {
    var list = $("#conv-list");
    var empty = $("#conv-empty");
    var items = state.conversations;
    list.textContent = "";

    if (!items.length) {
      list.hidden = true;
      empty.hidden = false;
      return;
    }

    list.hidden = false;
    empty.hidden = true;

    items.forEach(function (item) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "conv-item" + (item.session_id === state.active ? " active" : "");
      button.setAttribute("role", "listitem");

      var avatar = document.createElement("span");
      avatar.className = "conv-avatar";
      avatar.textContent = initial(item.name, item.source);

      var body = document.createElement("span");
      body.className = "conv-body";

      var top = document.createElement("span");
      top.className = "conv-top";
      var name = document.createElement("strong");
      name.className = "conv-name";
      name.textContent = displayName(item);
      var time = document.createElement("time");
      time.className = "conv-time";
      time.textContent = formatConvTime(item.updated_at);
      top.appendChild(name);
      top.appendChild(time);

      var contact = document.createElement("span");
      contact.className = "conv-contact" + (item.contact ? "" : " muted");
      contact.textContent = item.contact || "未留联系方式";

      var preview = document.createElement("span");
      preview.className = "conv-preview";
      preview.textContent = item.last_message || defaultPreview(item);

      body.appendChild(top);
      body.appendChild(contact);
      body.appendChild(preview);
      button.appendChild(avatar);
      button.appendChild(body);

      if (item.unread_admin > 0) {
        var badge = document.createElement("span");
        badge.className = "conv-unread";
        badge.textContent = item.unread_admin > 9 ? "9+" : String(item.unread_admin);
        button.appendChild(badge);
      }

      button.addEventListener("click", function () {
        openConversation(item.session_id);
      });
      list.appendChild(button);
    });
  }

  function displayName(item) {
    if (item.name) return item.name;
    if (item.source === "form") return "表单访客";
    return "访客";
  }

  function initial(name, source) {
    var value = String(name || "").trim();
    if (value) return value.charAt(0);
    return source === "form" ? "表" : "访";
  }

  function defaultPreview(item) {
    return item.source === "form" ? "提交了联系表单" : "开始咨询";
  }

  function openConversation(sessionId) {
    state.active = sessionId;
    $("#detail-empty").hidden = true;
    $("#detail").hidden = false;
    $("#inbox").classList.add("show-detail");
    renderList();
    loadDetail(true).then(function () {
      if (window.matchMedia("(min-width: 721px)").matches) {
        $("#reply-input").focus();
      }
    });
  }

  function loadDetail(scroll) {
    if (!state.active) return Promise.resolve();
    var session = encodeURIComponent(state.active);
    return api("/api/admin/conversations/" + session)
      .then(function (data) {
        state.detail = data;
        updateDetailHeader(data.conversation);
        var messages = data.messages || [];
        var lastId = messages.length ? Number(messages[messages.length - 1].id) : 0;
        if (scroll || lastId !== state.lastMessageId) {
          renderMessages(messages);
          state.lastMessageId = lastId;
          if (scroll) scrollMessages();
        }
        var item = findConversation(state.active);
        if (item && item.unread_admin) {
          item.unread_admin = 0;
          renderList();
          loadOverview();
        }
      })
      .catch(function (error) {
        if (error.status === 404) {
          clearDetail();
          loadConversations();
          toast("该会话不存在");
        } else if (error.status !== 401) {
          setConn(false);
        }
      });
  }

  function findConversation(sessionId) {
    for (var i = 0; i < state.conversations.length; i += 1) {
      if (state.conversations[i].session_id === sessionId) return state.conversations[i];
    }
    return null;
  }

  function updateDetailHeader(conversation) {
    if (!conversation) return;
    $("#detail-name").textContent = displayName(conversation);
    var contact = $("#detail-contact");
    contact.textContent = conversation.contact || "未留联系方式";
    contact.classList.toggle("muted", !conversation.contact);
    $("#detail-avatar").textContent = initial(conversation.name, conversation.source);
    var source = $("#detail-source");
    source.textContent = conversation.source === "form" ? "官网表单" : "在线咨询";
    source.classList.toggle("form", conversation.source === "form");
    $("#detail-time").textContent = formatFullTime(conversation.created_at);
  }

  function renderMessages(messages) {
    var container = $("#detail-messages");
    container.textContent = "";
    if (!messages.length) {
      var empty = document.createElement("p");
      empty.className = "reply-hint";
      empty.textContent = "还没有消息";
      container.appendChild(empty);
      return;
    }
    messages.forEach(function (message) {
      var role =
        message.role === "visitor" ? "visitor" : message.role === "admin" ? "admin" : "bot";
      var row = document.createElement("div");
      row.className = "dm dm-" + role;

      var avatar = document.createElement("span");
      avatar.className = "dm-avatar";
      avatar.textContent = role === "admin" ? "我" : role === "bot" ? "机" : "访";

      var content = document.createElement("div");
      content.className = "dm-content";

      var bubble = document.createElement("div");
      bubble.className = "dm-bubble";
      bubble.textContent = message.content;
      content.appendChild(bubble);

      var time = document.createElement("span");
      time.className = "dm-time";
      var author = role === "admin" ? "我" : role === "bot" ? "自动回复" : "访客";
      time.textContent = formatClock(message.created_at) + " · " + author;
      content.appendChild(time);

      row.appendChild(avatar);
      row.appendChild(content);
      container.appendChild(row);
    });
  }

  function scrollMessages() {
    var node = $("#detail-messages");
    if (!node) return;
    window.requestAnimationFrame(function () {
      node.scrollTop = node.scrollHeight;
    });
  }

  function clearDetail() {
    state.active = "";
    state.detail = null;
    state.lastMessageId = 0;
    $("#detail").hidden = true;
    $("#detail-empty").hidden = false;
    $("#inbox").classList.remove("show-detail");
    $("#detail-messages").textContent = "";
    $("#reply-input").value = "";
    renderList();
  }

  function sendReply() {
    var input = $("#reply-input");
    var content = input.value.trim();
    if (!content) {
      toast("请先输入回复内容");
      input.focus();
      return;
    }
    if (!state.active) return;
    var button = $("#reply-btn");
    button.disabled = true;
    button.textContent = "发送中…";

    api("/api/admin/conversations/" + encodeURIComponent(state.active) + "/messages", {
      method: "POST",
      body: JSON.stringify({ content: content })
    })
      .then(function (data) {
        input.value = "";
        var container = $("#detail-messages");
        var row = document.createElement("div");
        row.className = "dm dm-admin";
        var avatar = document.createElement("span");
        avatar.className = "dm-avatar";
        avatar.textContent = "我";
        var contentNode = document.createElement("div");
        contentNode.className = "dm-content";
        var bubble = document.createElement("div");
        bubble.className = "dm-bubble";
        bubble.textContent = data.message.content;
        var time = document.createElement("span");
        time.className = "dm-time";
        time.textContent = formatClock(data.message.created_at) + " · 我";
        contentNode.appendChild(bubble);
        contentNode.appendChild(time);
        row.appendChild(avatar);
        row.appendChild(contentNode);
        container.appendChild(row);
        state.lastMessageId = Math.max(state.lastMessageId, Number(data.message.id) || 0);
        scrollMessages();
        loadConversations(true);
        loadOverview();
        toast("已发送");
        input.focus();
      })
      .catch(function (error) {
        if (error.status !== 401) toast(error.message || "发送失败");
      })
      .finally(function () {
        button.disabled = false;
        button.textContent = "发送回复";
      });
  }

  /* ------------------------------------------------------------------ time */

  function parseDate(value) {
    var date = new Date(value);
    return isNaN(date.getTime()) ? null : date;
  }

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function formatClock(value) {
    var date = parseDate(value);
    if (!date) return "";
    return pad(date.getHours()) + ":" + pad(date.getMinutes());
  }

  function isSameDay(a, b) {
    return (
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate()
    );
  }

  function formatConvTime(value) {
    var date = parseDate(value);
    if (!date) return "";
    var now = new Date();
    if (isSameDay(date, now)) return formatClock(value);
    var yesterday = new Date(now.getTime() - 86400000);
    if (isSameDay(date, yesterday)) return "昨天";
    if (date.getFullYear() === now.getFullYear()) {
      return date.getMonth() + 1 + "月" + date.getDate() + "日";
    }
    return date.getFullYear() + "/" + (date.getMonth() + 1) + "/" + date.getDate();
  }

  function formatFullTime(value) {
    var date = parseDate(value);
    if (!date) return "";
    return (
      date.getFullYear() +
      "-" +
      pad(date.getMonth() + 1) +
      "-" +
      pad(date.getDate()) +
      " " +
      pad(date.getHours()) +
      ":" +
      pad(date.getMinutes())
    );
  }

  /* --------------------------------------------------------------- polling */

  function startPolling() {
    stopPolling();
    state.timer = window.setInterval(function () {
      if (document.hidden) return;
      if ($("#app-view").hidden) return;
      loadOverview();
      loadConversations(true);
      if (state.active) loadDetail(false);
    }, 8000);
  }

  function stopPolling() {
    if (state.timer) {
      window.clearInterval(state.timer);
      state.timer = null;
    }
  }

  /* ------------------------------------------------------------------- init */

  function loadAll() {
    loadOverview();
    loadConversations();
  }

  function exportCsv() {
    fetch("/api/admin/export.csv", {
      headers: { "X-Admin-Token": state.token },
      cache: "no-store"
    })
      .then(function (response) {
        if (response.status === 401) {
          logout("登录已过期，请重新登录");
          throw new Error("登录已过期");
        }
        if (!response.ok) throw new Error("导出失败");
        return response.blob();
      })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var link = document.createElement("a");
        link.href = url;
        link.download = "meike-leads-" + new Date().toISOString().slice(0, 10) + ".csv";
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(function () {
          URL.revokeObjectURL(url);
        }, 1000);
        toast("已导出 CSV");
      })
      .catch(function (error) {
        if (error.message !== "登录已过期") toast(error.message || "导出失败");
      });
  }

  function debounce(fn, wait) {
    var timer = null;
    return function () {
      var args = arguments;
      var context = this;
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        fn.apply(context, args);
      }, wait);
    };
  }

  function bind() {
    state.token = readToken();

    $("#login-form").addEventListener("submit", login);
    $("#toggle-password").addEventListener("click", function () {
      var input = $("#password");
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      this.textContent = show ? "隐藏" : "显示";
      input.focus();
    });
    $("#logout-btn").addEventListener("click", function () {
      logout();
    });
    $("#refresh-btn").addEventListener("click", function () {
      loadAll();
      if (state.active) loadDetail(false);
      toast("已刷新");
    });
    $("#refresh-list").addEventListener("click", function () {
      loadConversations();
    });
    $("#export-btn").addEventListener("click", exportCsv);
    $("#reply-btn").addEventListener("click", sendReply);
    $("#back-btn").addEventListener("click", function () {
      $("#inbox").classList.remove("show-detail");
    });
    $("#search-input").addEventListener(
      "input",
      debounce(function (event) {
        state.search = event.target.value.trim();
        loadConversations();
      }, 280)
    );
    $("#reply-input").addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        sendReply();
      }
    });
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden && state.token && !$("#app-view").hidden) {
        loadOverview();
        loadConversations(true);
        if (state.active) loadDetail(false);
      }
    });

    verifyToken();
  }

  document.addEventListener("DOMContentLoaded", bind);
})();
