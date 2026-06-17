/* =====================================================
   BRAINS COLLEGE — AI CHATBOT + LEAD FORM
   ===================================================== */

(function () {
  "use strict";

  const API_BASE  = window.location.origin;
  const API_CHAT  = `${API_BASE}/api/chat`;
  const API_LEAD  = `${API_BASE}/api/lead`;

  // =====================================================
  // STATE
  // =====================================================
  let isOpen       = false;
  let isTyping     = false;
  let conversation = [];
  let activeTab    = "chat"; // "chat" | "lead"

  // =====================================================
  // DOM REFS
  // =====================================================
  const $ = (id) => document.getElementById(id);

  const trigger         = $("chatTrigger");
  const panel           = $("chatPanel");
  const overlay         = $("chatOverlay");
  const closeBtn        = $("closeBtn");
  const clearBtn        = $("clearBtn");
  const sendBtn         = $("sendBtn");
  const userInput       = $("userInput");
  const msgBox          = $("messagesContainer");
  const typingEl        = $("typingIndicator");
  const quickTopics     = $("quickTopics");

  // Tabs
  const tabChatBtn      = $("tabChat");
  const tabLeadBtn      = $("tabLead");
  const chatTabEl       = $("chatTab");
  const leadTabEl       = $("leadTab");

  // Lead form
  const leadName        = $("leadName");
  const leadPhone       = $("leadPhone");
  const leadCampus      = $("leadCampus");
  const leadSubmitBtn   = $("leadSubmitBtn");
  const submitBtnText   = $("submitBtnText");
  const submitBtnSpinner= $("submitBtnSpinner");
  const submitError     = $("submitError");
  const leadSuccess     = $("leadSuccess");
  const leadFormFields  = $("leadFormFields");
  const leadAgainBtn    = $("leadAgainBtn");

  const nameError       = $("nameError");
  const phoneError      = $("phoneError");
  const campusError     = $("campusError");

  // =====================================================
  // OPEN / CLOSE
  // =====================================================
  function openPanel() {
    isOpen = true;
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");
    overlay.classList.add("active");
    trigger.classList.add("open");
    trigger.querySelector(".trigger-icon").innerHTML = closeSVG();
    if (activeTab === "chat") setTimeout(() => userInput.focus(), 350);
  }

  function closePanel() {
    isOpen = false;
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    overlay.classList.remove("active");
    trigger.classList.remove("open");
    trigger.querySelector(".trigger-icon").innerHTML = chatSVG();
  }

  function togglePanel() { isOpen ? closePanel() : openPanel(); }

  function chatSVG() {
    return `<svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z"
        stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  }

  function closeSVG() {
    return `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
  }

  // =====================================================
  // TAB SWITCHING
  // =====================================================
  function switchTab(tab) {
    activeTab = tab;
    if (tab === "chat") {
      tabChatBtn.classList.add("active");
      tabLeadBtn.classList.remove("active");
      chatTabEl.classList.remove("hidden");
      leadTabEl.classList.add("hidden");
      clearBtn.style.display = "";
      setTimeout(() => userInput.focus(), 100);
    } else {
      tabLeadBtn.classList.add("active");
      tabChatBtn.classList.remove("active");
      leadTabEl.classList.remove("hidden");
      chatTabEl.classList.add("hidden");
      clearBtn.style.display = "none";
    }
  }

  // =====================================================
  // CHAT RENDER HELPERS
  // =====================================================
  function renderMarkdown(text) {
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/^[\-\*] (.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");
    html = html.replace(/\n{2,}/g, "</p><p>");
    html = html.replace(/\n/g, "<br/>");
    return `<p>${html}</p>`;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/\n/g, "<br/>");
  }

  function formatTime() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function appendMessage(role, text) {
    if (role === "user" && quickTopics) quickTopics.style.display = "none";
    const div = document.createElement("div");
    div.className = `msg ${role}`;
    const avatarContent = role === "bot" ? "🎓" : "👤";
    const bubbleContent = role === "bot" ? renderMarkdown(text) : escapeHtml(text);
    div.innerHTML = `
      <div class="msg-avatar">${avatarContent}</div>
      <div>
        <div class="msg-bubble">${bubbleContent}</div>
        <div class="msg-time">${formatTime()}</div>
      </div>`;
    msgBox.appendChild(div);
    scrollToBottom();
  }

  function scrollToBottom() { msgBox.scrollTop = msgBox.scrollHeight; }

  function showTyping() { isTyping = true; typingEl.style.display = "flex"; scrollToBottom(); }
  function hideTyping() { isTyping = false; typingEl.style.display = "none"; }

  function showWelcome() {
    const card = document.createElement("div");
    card.className = "welcome-card";
    card.innerHTML = `
      <div class="wc-emoji">🎓</div>
      <h3>Welcome to Brains College!</h3>
      <p>I'm your AI assistant. Ask me about admissions, courses, fees, schedules, scholarships, or campuses.</p>`;
    msgBox.appendChild(card);
  }

  // =====================================================
  // SEND CHAT MESSAGE
  // =====================================================
  async function sendMessage(text) {
    text = text.trim();
    if (!text || isTyping) return;

    conversation.push({ role: "user", content: text });
    appendMessage("user", text);
    userInput.value = "";
    autoResize();
    sendBtn.disabled = true;
    showTyping();

    try {
      const res = await fetch(API_CHAT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: conversation })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${res.status}`);
      }
      const data = await res.json();
      hideTyping();
      if (data.success) {
        conversation.push({ role: "assistant", content: data.reply });
        appendMessage("bot", data.reply);
      } else {
        appendMessage("bot", "⚠️ Something went wrong. Please try again.");
      }
    } catch (err) {
      hideTyping();
      appendMessage("bot", `⚠️ ${err.message || "Network error. Please check your connection."}`);
    }
  }

  function clearConversation() {
    conversation = [];
    msgBox.innerHTML = "";
    if (quickTopics) quickTopics.style.display = "block";
    showWelcome();
  }

  function autoResize() {
    userInput.style.height = "auto";
    userInput.style.height = Math.min(userInput.scrollHeight, 100) + "px";
    sendBtn.disabled = userInput.value.trim().length === 0;
  }

  // =====================================================
  // LEAD FORM VALIDATION & SUBMISSION
  // =====================================================
  function clearFieldError(input, errorEl) {
    input.classList.remove("error");
    errorEl.textContent = "";
  }

  function setFieldError(input, errorEl, msg) {
    input.classList.add("error");
    errorEl.textContent = msg;
  }

  function validateLeadForm() {
    let valid = true;

    // Name
    const name = leadName.value.trim();
    if (!name) {
      setFieldError(leadName, nameError, "Please enter your full name.");
      valid = false;
    } else if (name.length < 2) {
      setFieldError(leadName, nameError, "Name must be at least 2 characters.");
      valid = false;
    } else {
      clearFieldError(leadName, nameError);
    }

    // Phone — simple Pakistan number check
    const phone = leadPhone.value.trim();
    const phoneRegex = /^(\+92|0)?[0-9\-\s]{9,15}$/;
    if (!phone) {
      setFieldError(leadPhone, phoneError, "Please enter your phone number.");
      valid = false;
    } else if (!phoneRegex.test(phone)) {
      setFieldError(leadPhone, phoneError, "Enter a valid phone number (e.g. 0300-1234567).");
      valid = false;
    } else {
      clearFieldError(leadPhone, phoneError);
    }

    // Campus
    const campus = leadCampus.value;
    if (!campus) {
      setFieldError(leadCampus, campusError, "Please select a campus.");
      valid = false;
    } else {
      clearFieldError(leadCampus, campusError);
    }

    return valid;
  }

  async function submitLead() {
    // Hide previous API error
    submitError.style.display = "none";

    if (!validateLeadForm()) return;

    // Show spinner
    leadSubmitBtn.disabled = true;
    submitBtnText.style.display = "none";
    submitBtnSpinner.style.display = "flex";

    const payload = {
      name:   leadName.value.trim(),
      phone:  leadPhone.value.trim(),
      campus: leadCampus.value
    };

    try {
      const res = await fetch(API_LEAD, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || `Server error ${res.status}`);
      }

      // SUCCESS — show success state
      leadFormFields.style.display = "none";
      leadSuccess.style.display    = "flex";
      leadSuccess.style.flexDirection = "column";
      leadSuccess.style.alignItems = "center";

    } catch (err) {
      submitError.textContent = `⚠️ ${err.message || "Submission failed. Please try again."}`;
      submitError.style.display = "block";
    } finally {
      leadSubmitBtn.disabled = false;
      submitBtnText.style.display = "";
      submitBtnSpinner.style.display = "none";
    }
  }

  function resetLeadForm() {
    leadName.value   = "";
    leadPhone.value  = "";
    leadCampus.value = "";
    clearFieldError(leadName,   nameError);
    clearFieldError(leadPhone,  phoneError);
    clearFieldError(leadCampus, campusError);
    submitError.style.display    = "none";
    leadSuccess.style.display    = "none";
    leadFormFields.style.display = "block";
  }

  // =====================================================
  // LIVE VALIDATION (on blur)
  // =====================================================
  leadName.addEventListener("blur", () => {
    const v = leadName.value.trim();
    if (v && v.length >= 2) clearFieldError(leadName, nameError);
  });

  leadPhone.addEventListener("blur", () => {
    const v = leadPhone.value.trim();
    const ok = /^(\+92|0)?[0-9\-\s]{9,15}$/.test(v);
    if (v && ok) clearFieldError(leadPhone, phoneError);
  });

  leadCampus.addEventListener("change", () => {
    if (leadCampus.value) clearFieldError(leadCampus, campusError);
  });

  // =====================================================
  // EVENT LISTENERS
  // =====================================================
  trigger.addEventListener("click", togglePanel);
  closeBtn.addEventListener("click", closePanel);
  overlay.addEventListener("click", closePanel);
  clearBtn.addEventListener("click", clearConversation);

  tabChatBtn.addEventListener("click", () => switchTab("chat"));
  tabLeadBtn.addEventListener("click", () => switchTab("lead"));

  sendBtn.addEventListener("click", () => sendMessage(userInput.value));

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(userInput.value);
    }
  });

  userInput.addEventListener("input", autoResize);

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const msg = chip.getAttribute("data-msg");
      if (msg) {
        if (!isOpen) openPanel();
        switchTab("chat");
        sendMessage(msg);
      }
    });
  });

  leadSubmitBtn.addEventListener("click", submitLead);
  leadAgainBtn.addEventListener("click", resetLeadForm);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && isOpen) closePanel();
  });

  // =====================================================
  // INIT
  // =====================================================
  showWelcome();
  sendBtn.disabled = true;
  clearBtn.style.display = "";

})();
