/* Meike Tech · H5 interactions: consultation chat, lead form, small UI touches. */
(function () {
  "use strict";

  var STORAGE_KEY = "meike_chat_session";
  var state = {
    sessionId: readSession(),
    lastId: 0,
    open: false,
    sending: false,
    contactSaved: false,
    rendered: {},
    pollTimer: null,
    unreadTimer: null,
    toastTimer: null,
    lastFocus: null
  };

  var $ = function (selector, scope) {
    return (scope || document).querySelector(selector);
  };
  var $$ = function (selector, scope) {
    return Array.prototype.slice.call((scope || document).querySelectorAll(selector));
  };

  /* ---------------------------------------------------------------- helpers */

  function readSession() {
    try {
      return window.localStorage.getItem(STORAGE_KEY) || "";
    } catch (error) {
      return "";
    }
  }

  function writeSession(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch (error) {
      /* private mode: keep it in memory only */
    }
  }

  function newSessionId() {
    var id = "";
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      id = window.crypto.randomUUID();
    } else {
      id = "mk-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
    }
    return id;
  }

  function api(path, options) {
    options = options || {};
    var headers = { "Content-Type": "application/json" };
    if (options.headers) {
      Object.keys(options.headers).forEach(function (key) {
        headers[key] = options.headers[key];
      });
    }
    return fetch(path, {
      method: options.method || "GET",
      headers: headers,
      body: options.body,
      cache: "no-store",
      credentials: "same-origin"
    })
      .then(function (response) {
        return response
          .json()
          .catch(function () {
            return null;
          })
          .then(function (data) {
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

  function toast(message) {
    var node = $("#toast");
    if (!node) return;
    node.textContent = message;
    node.classList.add("show");
    window.clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(function () {
      node.classList.remove("show");
    }, 2800);
  }

  function scrollChat() {
    var body = $("#chat-body");
    if (!body) return;
    window.requestAnimationFrame(function () {
      body.scrollTop = body.scrollHeight;
    });
  }

  function timeLabel(iso) {
    var date = new Date(iso);
    if (isNaN(date.getTime())) return "";
    var hh = String(date.getHours()).padStart(2, "0");
    var mm = String(date.getMinutes()).padStart(2, "0");
    return hh + ":" + mm;
  }

  function isMobileChat() {
    return window.matchMedia("(max-width: 560px)").matches;
  }

  /* ------------------------------------------------------------ chat render */

  function createMessageNode(message) {
    var role = message.role === "visitor" ? "user" : message.role === "admin" ? "admin" : "bot";
    var wrap = document.createElement("div");
    wrap.className = "msg msg-" + role;

    if (role !== "user") {
      var avatar = document.createElement("span");
      avatar.className = "msg-avatar";
      avatar.textContent = role === "admin" ? "顾" : "美";
      wrap.appendChild(avatar);
    }

    var content = document.createElement("div");
    content.className = "msg-content";

    var bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = message.content;
    content.appendChild(bubble);

    var time = document.createElement("span");
    time.className = "msg-time";
    time.textContent = timeLabel(message.created_at);
    content.appendChild(time);

    wrap.appendChild(content);
    return wrap;
  }

  function renderMessage(message) {
    if (!message || message.id == null) return;
    if (state.rendered[String(message.id)]) return;
    state.rendered[String(message.id)] = true;
    state.lastId = Math.max(state.lastId, Number(message.id) || 0);
    $("#chat-messages").appendChild(createMessageNode(message));
  }

  function renderMessages(messages, scroll) {
    (messages || []).forEach(renderMessage);
    updateIntroState();
    if (scroll) scrollChat();
  }

  function updateIntroState() {
    var chips = $("#quick-replies");
    var messages = $("#chat-messages");
    if (chips && messages && messages.children.length > 0) {
      chips.hidden = true;
    }
  }

  function ensureSession() {
    if (state.sessionId) return Promise.resolve(state.sessionId);
    return api("/api/chat/sessions", {
      method: "POST",
      body: JSON.stringify({
        source: "chat",
        page: window.location.pathname
      })
    }).then(function (data) {
      state.sessionId = data.session_id;
      writeSession(state.sessionId);
      // A brand-new conversation did not have a polling timer yet.
      if (state.open) startPolling();
      return state.sessionId;
    });
  }

  /* -------------------------------------------------------------- chat open */

  function openChat(prefill) {
    if (state.open) {
      if (prefill) fillComposer(prefill);
      return;
    }
    state.lastFocus = document.activeElement;
    state.open = true;
    $("#chat-panel").classList.add("open");
    $("#chat-panel").setAttribute("aria-hidden", "false");
    $("#chat-fab").setAttribute("aria-expanded", "true");
    $("#chat-badge").hidden = true;

    if (isMobileChat()) {
      document.body.classList.add("chat-locked");
      $("#chat-backdrop").hidden = false;
      window.requestAnimationFrame(function () {
        $("#chat-backdrop").classList.add("show");
      });
    }

    if (prefill) fillComposer(prefill);

    if (state.sessionId) {
      fetchMessages(true);
    }
    startPolling();

    if (!isMobileChat()) {
      window.setTimeout(function () {
        var input = $("#chat-input");
        if (input) input.focus();
      }, 180);
    }
  }

  function closeChat() {
    if (!state.open) return;
    state.open = false;
    $("#chat-panel").classList.remove("open");
    $("#chat-panel").setAttribute("aria-hidden", "true");
    $("#chat-fab").setAttribute("aria-expanded", "false");
    document.body.classList.remove("chat-locked");
    $("#chat-backdrop").classList.remove("show");
    window.setTimeout(function () {
      if (!state.open) $("#chat-backdrop").hidden = true;
    }, 220);
    stopPolling();
    startUnreadPolling();
    if (state.lastFocus && state.lastFocus.focus) {
      state.lastFocus.focus();
    }
  }

  function fillComposer(text) {
    var input = $("#chat-input");
    if (!input) return;
    input.value = text;
    autoGrow(input);
    if (!isMobileChat()) input.focus();
  }

  function autoGrow(input) {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 92) + "px";
  }

  /* ------------------------------------------------------------- messages API */

  function fetchMessages(scroll) {
    if (!state.sessionId) return Promise.resolve();
    var session = encodeURIComponent(state.sessionId);
    return api("/api/chat/sessions/" + session + "/messages?after_id=" + state.lastId)
      .then(function (data) {
        if (!data || !data.messages) return;
        var hadMessages = $("#chat-messages").children.length > 0;
        renderMessages(data.messages, scroll || hadMessages);
        if (data.messages.length) scrollChat();
      })
      .catch(function (error) {
        if (error.status === 404) resetSession();
      });
  }

  function resetSession() {
    state.sessionId = "";
    state.lastId = 0;
    state.rendered = {};
    writeSession("");
    stopPolling();
    var badge = $("#chat-badge");
    if (badge) badge.hidden = true;
    var messages = $("#chat-messages");
    if (messages) messages.textContent = "";
  }

  function sendMessage(rawText) {
    var text = String(rawText || "").trim();
    if (!text || state.sending) return;
    var input = $("#chat-input");
    state.sending = true;
    var button = $(".chat-send");
    if (button) button.disabled = true;
    var temp = null;

    ensureSession()
      .then(function (sessionId) {
        temp = createMessageNode({
          role: "visitor",
          content: text,
          created_at: new Date().toISOString()
        });
        $("#chat-messages").appendChild(temp);
        $("#quick-replies").hidden = true;
        scrollChat();
        if (input) {
          input.value = "";
          autoGrow(input);
        }

        return api("/api/chat/sessions/" + encodeURIComponent(sessionId) + "/messages", {
          method: "POST",
          body: JSON.stringify({ content: text })
        }).then(function (data) {
          if (temp && temp.parentNode) temp.parentNode.removeChild(temp);
          temp = null;
          renderMessage(data.message);
          if (data.reply) {
            window.setTimeout(function () {
              renderMessage(data.reply);
              scrollChat();
            }, 320);
          }
          scrollChat();
        });
      })
      .catch(function (error) {
        if (temp && temp.parentNode) temp.parentNode.removeChild(temp);
        temp = null;
        toast(error.message || "发送失败，请稍后再试");
        if (input && !input.value) {
          input.value = text;
          autoGrow(input);
        }
      })
      .finally(function () {
        state.sending = false;
        if (button) button.disabled = false;
        if (!isMobileChat() && input) input.focus();
      });
  }

  /* ------------------------------------------------------------- polling */

  function startPolling() {
    stopPolling();
    if (!state.sessionId) return;
    state.pollTimer = window.setInterval(function () {
      if (state.open && !document.hidden) fetchMessages(false);
    }, 3500);
  }

  function stopPolling() {
    if (state.pollTimer) {
      window.clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function startUnreadPolling() {
    stopUnreadPolling();
    if (!state.sessionId) return;
    checkUnread();
    state.unreadTimer = window.setInterval(function () {
      if (!state.open && !document.hidden) checkUnread();
    }, 25000);
  }

  function stopUnreadPolling() {
    if (state.unreadTimer) {
      window.clearInterval(state.unreadTimer);
      state.unreadTimer = null;
    }
  }

  function checkUnread() {
    if (!state.sessionId || state.open) return;
    api("/api/chat/sessions/" + encodeURIComponent(state.sessionId) + "/unread")
      .then(function (data) {
        var count = (data && data.count) || 0;
        var badge = $("#chat-badge");
        if (!badge) return;
        if (count > 0) {
          badge.textContent = count > 9 ? "9+" : String(count);
          badge.hidden = false;
        } else {
          badge.hidden = true;
        }
      })
      .catch(function () {
        /* silent */
      });
  }

  /* --------------------------------------------------------------- contact */

  function openContactModal() {
    state.lastFocus = document.activeElement;
    $("#contact-modal").hidden = false;
    var first = $("#contact-form input[name='name']");
    if (first) window.setTimeout(function () { first.focus(); }, 60);
  }

  function closeContactModal() {
    $("#contact-modal").hidden = true;
    if (state.lastFocus && state.lastFocus.focus) state.lastFocus.focus();
  }

  function submitContact(form) {
    var data = new FormData(form);
    var name = String(data.get("name") || "").trim();
    var contact = String(data.get("contact") || "").trim();
    if (contact.length < 2) {
      toast("请填写手机号或微信号");
      return;
    }
    var button = form.querySelector("button[type='submit']");
    if (button) {
      button.disabled = true;
      button.textContent = "提交中…";
    }

    ensureSession()
      .then(function (sessionId) {
        return api("/api/chat/sessions/" + encodeURIComponent(sessionId) + "/contact", {
          method: "POST",
          body: JSON.stringify({ name: name, contact: contact })
        });
      })
      .then(function (result) {
        state.contactSaved = true;
        closeContactModal();
        form.reset();
        toast("已收到，顾问会尽快联系你");
        if (result && result.reply) {
          renderMessage(result.reply);
          scrollChat();
        }
        var bar = $("#chat-contact-btn");
        if (bar) {
          bar.disabled = true;
          var title = bar.querySelector(".ccb-text strong");
          var sub = bar.querySelector(".ccb-text small");
          var action = bar.querySelector(".ccb-action");
          if (title) title.textContent = "联系方式已收到";
          if (sub) sub.textContent = "顾问会尽快联系你";
          if (action) action.textContent = "✓";
        }
        if (!state.open) openChat();
      })
      .catch(function (error) {
        toast(error.message || "提交失败，请稍后再试");
      })
      .finally(function () {
        if (button) {
          button.disabled = false;
          button.textContent = "提交";
        }
      });
  }

  /* ------------------------------------------------------------ lead form */

  function submitLead(form) {
    var data = new FormData(form);
    if (String(data.get("website") || "").trim() !== "") {
      showLeadSuccess();
      return;
    }
    var contact = String(data.get("contact") || "").trim();
    if (contact.length < 2) {
      toast("请填写手机号或微信号");
      var input = form.querySelector("input[name='contact']");
      if (input) input.focus();
      return;
    }
    var button = form.querySelector("button[type='submit']");
    if (button) {
      button.disabled = true;
      button.textContent = "提交中…";
    }

    api("/api/leads", {
      method: "POST",
      body: JSON.stringify({
        name: String(data.get("name") || "").trim(),
        contact: contact,
        requirement: String(data.get("requirement") || "").trim(),
        source: "form"
      })
    })
      .then(function () {
        showLeadSuccess();
      })
      .catch(function (error) {
        toast(error.message || "提交失败，请稍后再试");
        if (button) {
          button.disabled = false;
          button.textContent = "提交，等顾问联系我";
        }
      });
  }

  function showLeadSuccess() {
    $("#lead-form-el").hidden = true;
    $("#lead-success").hidden = false;
  }

  /* --------------------------------------------------------------- bindings */

  function bind() {
    $$("[data-chat-open]").forEach(function (button) {
      button.addEventListener("click", function () {
        openChat();
      });
    });

    $("#chat-fab").addEventListener("click", function () {
      if (state.open) closeChat();
      else openChat();
    });
    $("#chat-close").addEventListener("click", closeChat);
    $("#chat-backdrop").addEventListener("click", closeChat);

    $("#chat-form").addEventListener("submit", function (event) {
      event.preventDefault();
      sendMessage($("#chat-input").value);
    });

    $("#chat-input").addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage($("#chat-input").value);
      }
    });
    $("#chat-input").addEventListener("input", function (event) {
      autoGrow(event.target);
    });

    $("#quick-replies").addEventListener("click", function (event) {
      var button = event.target.closest("button[data-quick]");
      if (!button) return;
      sendMessage(button.getAttribute("data-quick"));
    });

    $$(".service-card").forEach(function (card) {
      card.addEventListener("click", function () {
        var ask = card.getAttribute("data-ask") || "";
        openChat(ask);
        toast("已填入咨询内容，点击发送即可");
      });
    });

    $("#chat-contact-btn").addEventListener("click", function () {
      if (state.contactSaved) return;
      openContactModal();
    });
    $("#contact-form").addEventListener("submit", function (event) {
      event.preventDefault();
      submitContact(event.target);
    });
    $$("[data-close-modal]").forEach(function (node) {
      node.addEventListener("click", closeContactModal);
    });

    $("#lead-form-el").addEventListener("submit", function (event) {
      event.preventDefault();
      submitLead(event.target);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      if (!$("#contact-modal").hidden) closeContactModal();
      else if (state.open) closeChat();
    });

    // Sticky header shadow.
    var header = $("#site-header");
    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        header.classList.toggle("scrolled", window.scrollY > 8);
        ticking = false;
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    document.addEventListener("visibilitychange", function () {
      if (document.hidden) return;
      if (state.open) fetchMessages(true);
      else if (state.sessionId) checkUnread();
    });

    // Hide the floating button while the contact section (with its own CTA
    // and form) fills the viewport, so it never covers the form.
    var contactSection = $("#contact");
    var fab = $("#chat-fab");
    if (contactSection && fab && "IntersectionObserver" in window) {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            var covered = entry.isIntersecting && entry.intersectionRatio >= 0.12;
            fab.classList.toggle("fab-hidden", covered);
          });
        },
        { threshold: [0, 0.12, 0.3] }
      );
      observer.observe(contactSection);
    }

    // Deep link: /?chat=1 opens the widget (useful for WeChat menu entry).
    var params = new URLSearchParams(window.location.search);
    if (params.get("chat") === "1") {
      window.setTimeout(function () {
        openChat(params.get("ask") || "");
      }, 500);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    bind();
    if (state.sessionId) startUnreadPolling();
  });
})();
