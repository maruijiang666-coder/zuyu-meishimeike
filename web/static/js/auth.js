/* Phone + SMS login page, and the logout action on the account page. */
(function () {
  "use strict";

  var $ = function (selector) {
    return document.querySelector(selector);
  };

  function api(path, options) {
    options = options || {};
    return fetch(path, {
      method: options.method || "GET",
      headers: { "Content-Type": "application/json" },
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
          if (!response.ok) {
            var detail = data && data.detail;
            if (Array.isArray(detail)) detail = detail[0] && detail[0].msg;
            var error = new Error(typeof detail === "string" ? detail : "网络开小差了，请稍后再试");
            error.status = response.status;
            throw error;
          }
          return data;
        });
    });
  }

  function digitsOnly(input, maxLength) {
    input.addEventListener("input", function () {
      var value = input.value.replace(/\D/g, "").slice(0, maxLength);
      if (input.value !== value) input.value = value;
    });
  }

  function showError(message) {
    var node = $("#auth-error");
    if (!node) return;
    node.textContent = message;
    node.hidden = !message;
  }

  function showDebug(code) {
    var node = $("#auth-debug");
    if (!node || !code) return;
    node.textContent = "开发模式验证码：" + code + "（仅本地生效，生产请关闭 SMS_DEBUG）";
    node.hidden = false;
  }

  function validPhone(value) {
    return /^1[3-9]\d{9}$/.test(value);
  }

  /* ------------------------------------------------------------- login page */

  function bindLogin() {
    var form = $("#login-form");
    if (!form) return;
    var phoneInput = $("#phone");
    var codeInput = $("#code");
    var sendButton = $("#send-code");
    var submitButton = $("#login-submit");
    var timer = null;
    var cooldownUntil = 0;

    digitsOnly(phoneInput, 11);
    digitsOnly(codeInput, 6);

    function setCountdown(seconds) {
      cooldownUntil = Date.now() + seconds * 1000;
      try {
        window.sessionStorage.setItem("meike_sms_until", String(cooldownUntil));
      } catch (error) {
        /* ignore */
      }
      window.clearInterval(timer);
      tick();
      timer = window.setInterval(tick, 1000);
    }

    function tick() {
      var left = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000));
      if (left <= 0) {
        window.clearInterval(timer);
        sendButton.disabled = false;
        sendButton.textContent = "重新获取";
        return;
      }
      sendButton.disabled = true;
      sendButton.textContent = left + "s 后可重发";
    }

    try {
      var saved = Number(window.sessionStorage.getItem("meike_sms_until") || 0);
      if (saved > Date.now()) {
        cooldownUntil = saved;
        tick();
        timer = window.setInterval(tick, 1000);
      }
    } catch (error) {
      /* ignore */
    }

    sendButton.addEventListener("click", function () {
      var phone = phoneInput.value.trim();
      showError("");
      if (!validPhone(phone)) {
        showError("请输入正确的 11 位手机号");
        phoneInput.focus();
        return;
      }
      sendButton.disabled = true;
      sendButton.textContent = "发送中…";
      api("/api/auth/send-code", {
        method: "POST",
        body: JSON.stringify({ phone: phone })
      })
        .then(function (data) {
          setCountdown(data.cooldown || 60);
          showDebug(data.debug_code || "");
          codeInput.focus();
        })
        .catch(function (error) {
          sendButton.disabled = false;
          sendButton.textContent = "获取验证码";
          showError(error.message || "验证码发送失败");
        });
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var phone = phoneInput.value.trim();
      var code = codeInput.value.trim();
      showError("");
      if (!validPhone(phone)) {
        showError("请输入正确的 11 位手机号");
        phoneInput.focus();
        return;
      }
      if (!/^\d{6}$/.test(code)) {
        showError("请输入 6 位短信验证码");
        codeInput.focus();
        return;
      }
      submitButton.disabled = true;
      submitButton.textContent = "登录中…";
      api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ phone: phone, code: code })
      })
        .then(function () {
          var next = document.body.getAttribute("data-next") || "/account";
          window.location.assign(next);
        })
        .catch(function (error) {
          showError(error.message || "登录失败，请稍后再试");
          submitButton.disabled = false;
          submitButton.textContent = "登录 / 注册";
        });
    });

    [phoneInput, codeInput].forEach(function (input) {
      input.addEventListener("input", function () {
        showError("");
      });
    });
  }

  /* ------------------------------------------------------------ account page */

  function bindLogout() {
    var button = $("#logout-btn");
    if (!button) return;
    button.addEventListener("click", function () {
      button.disabled = true;
      button.textContent = "退出中…";
      api("/api/auth/logout", { method: "POST" })
        .catch(function () {
          /* Even if the request fails, clear the client-side view. */
        })
        .finally(function () {
          window.location.assign("/");
        });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindLogin();
    bindLogout();
  });
})();
