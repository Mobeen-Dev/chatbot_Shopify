/**
 * ChatBotService - Handles streaming SSE-style responses reliably and safely.
 * Replaces previous functions that expected a single JSON response.
 */
class ChatBotService {
  constructor() {
    // DOM Elements
    this.chatToggle = document.getElementById("chat-toggle");
    this.chatWindow = document.getElementById("chat-window");
    this.minimizeChat = document.getElementById("minimize-chat");
    this.chatMessages = document.getElementById("chat-messages");
    this.chatInput = document.getElementById("chat-input");
    this.sendButton = document.getElementById("send-button");

    // State
    this.cartId = "";
    this.sessionId = null;
    this.conversationHistory = [];
    this.rememberMode = false;

    // Request control
    this.abortController = null;
    this.isAITyping = false;
    this.isProcessingRequest = false;

    // Config
    this.config = {
      timeout: 50000, // ms - abort if no response in this time
      maxRetries: 3,
      retryDelay: 1000,
      apiEndpoint: "https://jay-willing-rodent.ngrok-free.app/test-stream-chat",
    };

    // Cache
    this.responseCache = new Map();

    this.initUI();
  }

  initUI() {
    if (this.chatToggle) {
      this.chatToggle.addEventListener("click", () => this.toggleChatWindow());
    }
    if (this.minimizeChat) {
      this.minimizeChat.addEventListener("click", () =>
        this.minimizeChatWindow(),
      );
    }
    if (this.sendButton) {
      this.sendButton.addEventListener("click", () => this.sendMessage());
    }

    if (this.chatInput) {
      this.chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });

      this.chatInput.addEventListener("input", function () {
        this.style.height = "auto";
        const newHeight = Math.min(this.scrollHeight, 120);
        this.style.height = newHeight + "px";
      });
    }
  }

  toggleChatWindow() {
    if (!this.chatWindow || !this.chatToggle) return;
    this.chatWindow.classList.toggle("open");
    const icon = this.chatToggle.querySelector(".chat-icon");
    if (this.chatWindow.classList.contains("open")) {
      if (icon) icon.textContent = "close";
      this.chatInput?.focus();
    } else {
      if (icon) icon.textContent = "chat";
    }
  }

  minimizeChatWindow() {
    if (!this.chatWindow || !this.chatToggle) return;
    this.chatWindow.classList.remove("open");
    const icon = this.chatToggle.querySelector(".chat-icon");
    if (icon) icon.textContent = "chat";
  }

  // Always returns the created message element (so streaming can update safely)
  // addMessage(text, sender = "bot") {
  //   // allow creating an empty bubble for streaming (don't early-return on empty)
  //   const messageDiv = document.createElement("div");
  //   messageDiv.classList.add("message", `${sender}-message`);
  //   // Use innerHTML for HTML-aware messages; for plain text we escape when needed.
  //   messageDiv.innerHTML = text || "";
  //   this.chatMessages.appendChild(messageDiv);
  //   this.scrollToBottom();
  //   return messageDiv;
  // }

  addMessage(text, sender = "bot") {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", `${sender}-message`);

    // 1. Create a wrapper for the text
    const textSpan = document.createElement("span");
    textSpan.classList.add("message-text");
    textSpan.innerHTML = text || "";
    messageDiv.appendChild(textSpan);

    // 2. Add copy button (usually most useful for bot responses)
    if (text) {
      const copyBtn = document.createElement("button");
      copyBtn.className = "shop-ai-copy-btn";
      copyBtn.setAttribute("title", "Copy text");
      copyBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>`;

      copyBtn.onclick = () => this.copyToClipboard(text, copyBtn);
      messageDiv.appendChild(copyBtn);
    }

    this.chatMessages.appendChild(messageDiv);
    this.scrollToBottom();
    return messageDiv;
  }

  // 3. The Copy Function
  copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
      // Visual feedback: Change icon temporarily
      const originalHTML = btn.innerHTML;
      btn.innerHTML = "✓"; // Simple checkmark
      btn.classList.add("copied");

      setTimeout(() => {
        btn.innerHTML = originalHTML;
        btn.classList.remove("copied");
      }, 2000);
    });
  }

  addSystemMessage(text) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", "system-message");
    messageDiv.innerHTML = text;
    this.chatMessages.appendChild(messageDiv);
    this.scrollToBottom();
    setTimeout(() => {
      if (messageDiv.parentNode) {
        messageDiv.style.opacity = "0";
        setTimeout(() => {
          if (messageDiv.parentNode) messageDiv.remove();
        }, 300);
      }
    }, 5000);
  }

  addProductsFromResponse(products) {
    this.addMessage("Products recommendations :", "bot");

    const sortedProducts = products.sort((a, b) => {
      const priceA = parseFloat((a.price || "").replace(/[^0-9.-]+/g, "")) || 0;
      const priceB = parseFloat((b.price || "").replace(/[^0-9.-]+/g, "")) || 0;
      return priceA - priceB;
    });

    sortedProducts.forEach((product, index) => {
      setTimeout(() => this.addProduct(product), index * 300);
    });
  }

  addProduct(product) {
    const desc =
      product.description || product.title || JSON.stringify(product);
    this.addMessage(this.escapeHtml(desc).slice(1, -1), "bot");
    const productDiv = document.createElement("div");
    productDiv.classList.add("message", "bot-message");

    const productLink = document.createElement("a");
    productLink.classList.add("product-card");
    productLink.href = product.link || "#";
    productLink.target = "_blank";
    productLink.rel = "noopener noreferrer";

    productLink.innerHTML = `
      <img src="${product.imageurl || ""}" alt="${this.escapeHtml(product.title || "")}" class="product-image" />
      <div class="product-info">
        <h4 class="product-title">${this.escapeHtml(product.title || "")}</h4>
        <p class="product-price">${this.escapeHtml(product.price || "")}</p>
      </div>
    `;

    productDiv.appendChild(productLink);
    this.chatMessages.appendChild(productDiv);
    this.scrollToBottom();
  }

  addCartFromResponse(cart) {
    const cartDiv = document.createElement("div");
    cartDiv.classList.add("message", "bot-message", "cart-wrapper");

    let html = `<p class="cart-header">🛒 Here's your cart:</p><hr class="cart-header-divider">`;

    if (!cart.lineItems || !cart.lineItems.length) {
      html += `<p>Your cart is empty.</p><hr class="divider">`;
    } else {
      html += `<div class="cart-products">`;
      cart.lineItems.forEach((item, index) => {
        const title = item.merchandise_title || "Unnamed product";
        const qty = item.quantity || 1;
        const price = item.merchandise_price || "Price Not Confirmed";
        const safeTitle = title.length > 50 ? title.slice(0, 50) + "…" : title;
        html += `
          <div class="cart-item">
            <span class="cart-title">${this.escapeHtml(safeTitle)}</span>
            <span class="cart-price">${this.escapeHtml(price)} × ${qty}</span>
          </div>
        `;
        if (index < cart.lineItems.length - 1) html += `<hr class="divider">`;
      });
      html += `</div>`;
      html += `<hr class="divider subtotal-divider">`;
      html += `<p class="subtotal">Subtotal: ${this.escapeHtml(cart.subtotalAmount || "$0.00")}</p>`;
      if (cart.checkoutUrl) {
        html += `<a class="checkout-link" href="${this.escapeHtml(cart.checkoutUrl)}" target="_blank" rel="noopener noreferrer">Proceed to Checkout — ${this.escapeHtml(cart.subtotalAmount || "")}</a>`;
      }
    }

    cartDiv.innerHTML = html;
    this.chatMessages.appendChild(cartDiv);
    this.scrollToBottom();
  }

  addOrderFromResponse(order) {
    const orderDiv = document.createElement("div");
    orderDiv.classList.add("message", "bot-message", "order-wrapper");

    const safe = (val, fallback = "—") =>
      val && String(val).trim() ? this.escapeHtml(val) : fallback;

    let html = `<p class="order-header">📦 Your Order Summary</p><hr class="order-divider">`;
    html += `<div class="order-info">`;
    html += `<div class="order-row"><strong>Order ID:</strong> ${safe(order.OrderID)}</div>`;
    html += `<div class="order-row"><strong>Status:</strong> ${safe(order.FinancialStatus)} / ${safe(order.FulfillmentStatus)}</div>`;
    html += `<div class="order-row"><strong>Customer:</strong> ${safe(order.CustomerName)}</div>`;
    html += `<div class="order-row"><strong>Phone:</strong> ${safe(order.CustomerPhone)}</div>`;
    html += `<div class="order-row"><strong>Email:</strong> ${safe(order.CustomerEmail)}</div>`;

    if (order.Items) {
      const items = String(order.Items)
        .split("^break^")
        .map((s) => s.trim())
        .filter(Boolean);
      html += `<div class='order-row'><strong>Items:</strong><br>${items.map((it) => this.escapeHtml(it)).join("<br>")}</div>`;
    }

    if (order.ShippingAddress) {
      html += `<div class="order-row"><strong>Ship To:</strong> ${safe(order.ShippingAddress)}</div>`;
    }

    html += `<div class="order-row total"><strong>Total:</strong> ${safe(order.Total, "$0.00")}</div>`;
    html += `</div>`;

    orderDiv.innerHTML = html;
    this.chatMessages.appendChild(orderDiv);
    this.scrollToBottom();
  }

  addCartItem(item) {
    const productDiv = document.createElement("div");
    productDiv.classList.add("message", "bot-message");
    const productLink = document.createElement("div");
    productLink.classList.add("product-card");
    const title = item.merchandise?.title || "Unnamed product";
    const qty = item.quantity || 1;
    const price = item.price || "";
    productLink.innerHTML = `
      <div class="product-info">
        <h4 class="product-title">${this.escapeHtml(title)}</h4>
        <p class="product-price">${this.escapeHtml(price)} × ${qty}</p>
      </div>
    `;
    productDiv.appendChild(productLink);
    this.chatMessages.appendChild(productDiv);
    this.scrollToBottom();
  }

  showTypingIndicator() {
    this.isAITyping = true;
    // avoid duplicate typing indicator
    if (document.getElementById("typing-indicator")) return;
    const typingDiv = document.createElement("div");
    typingDiv.classList.add("typing-indicator");
    typingDiv.id = "typing-indicator";
    typingDiv.innerHTML = `
      <div class="dot"></div><div class="dot"></div><div class="dot"></div>
      <span class="text">Assistant is typing...</span>
    `;
    this.chatMessages.appendChild(typingDiv);
    this.scrollToBottom();
  }

  hideTypingIndicator() {
    this.isAITyping = false;
    const typingIndicator = document.getElementById("typing-indicator");
    if (typingIndicator) typingIndicator.remove();
  }

  setInputDisabled(disabled) {
    if (this.chatInput) this.chatInput.disabled = disabled;
    if (this.sendButton) this.sendButton.disabled = disabled;
    if (!disabled) this.chatInput?.focus();
  }

  scrollToBottom() {
    if (this.chatMessages)
      this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text ?? "";
    return div.innerHTML;
  }

  delay(ms) {
    return new Promise((res) => setTimeout(res, ms));
  }

  isRetryableError(error) {
    if (!error || !error.message) return false;
    const retryableErrors = [
      "NetworkError",
      "Failed to fetch",
      "TypeError",
      "HTTP 429",
      "timeout",
    ];
    return retryableErrors.some((err) => error.message.includes(err));
  }

  handleError(error) {
    console.error("ChatBot error:", error);
    this.addMessage(
      `⚠️ Error: ${this.escapeHtml(error.message || String(error))}`,
      "error",
    );
  }

  /**
   * makeRequest - POSTs and returns the Response object (so we can stream the body)
   * - supports retries on network-ish errors
   * - does NOT attempt to parse response.json() because server streams SSE
   */
  async makeRequest(data, retryCount = 0) {
    try {
      // Abort controller for this request
      if (this.abortController) {
        // if a previous controller exists, abort it to avoid concurrency issues
        try {
          this.abortController.abort();
        } catch (e) {
          /* ignore */
        }
      }
      this.abortController = new AbortController();

      // Setup timeout: call abort after config.timeout
      const timeoutId = setTimeout(() => {
        try {
          this.abortController.abort();
        } catch (e) {
          /* ignore */
        }
      }, this.config.timeout);

      const res = await fetch(this.config.apiEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream", // indicate we expect SSE
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(data),
        signal: this.abortController.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        // treat non-2xx as error (allow retry logic to catch this)
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      return res; // caller will consume res.body as stream
    } catch (error) {
      // Retry for network-ish transient errors
      if (retryCount < this.config.maxRetries && this.isRetryableError(error)) {
        await this.delay(this.config.retryDelay * Math.pow(2, retryCount));
        return this.makeRequest(data, retryCount + 1);
      }
      throw error;
    }
  }

  /**
   * getAIResponse - consume SSE stream and update UI incrementally
   * Returns an object: { reply: finalText, structural_data: [], session_id }
   */
  async getAIResponse(message) {
    const cacheKey = this.rememberMode
      ? `${message}_${JSON.stringify(this.conversationHistory)}`
      : message;

    if (this.responseCache.has(cacheKey)) {
      return {
        reply: this.responseCache.get(cacheKey),
        structural_data: [],
        session_id: this.sessionId,
      };
    }

    const payload = { message, session_id: this.sessionId || null };
    const response = await this.makeRequest(payload);
    if (!response || !response.body) throw new Error("No stream available");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    // Create permanent wrapper bubble
    const botEl = this.addMessage("", "bot");
    this.hideTypingIndicator();

    // Streaming state
    let accumulated = "";
    let buffer = "";
    let structural_data = [];
    let finalSessionId = this.sessionId;

    // Helper: live markdown render without replacing wrapper
    const safeRender = (text) => {
      // render to HTML
      const html = this.renderMarkdown(text);

      // Prevent layout shift:
      // Instead of replacing the element, update only its inside
      botEl.innerHTML = html;
      // this.scrollToBottom();
    };

    // Helper: apply token chunk
    const applyChunk = (token) => {
      accumulated += token;

      // smooth markdown streaming:
      // small markdown renderer calls are cheap,
      // this gives a ChatGPT-like effect
      safeRender(accumulated);
    };

    const parseEvent = (part) => {
      const lines = part.split(/\r?\n/);
      const dataLines = [];

      for (const line of lines) {
        if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }

      if (!dataLines.length) return true;

      const data = dataLines.join("\n");

      if (data === "[DONE]") return false;

      // Try JSON token
      try {
        const parsed = JSON.parse(data);

        if (parsed.session_id) finalSessionId = parsed.session_id;
        if (parsed.structural_data)
          structural_data.push(...parsed.structural_data);

        if (parsed.text || parsed.chunk || parsed.content) {
          applyChunk(String(parsed.text || parsed.chunk || parsed.content));
        }
        return true;
      } catch (_) {
        // raw text
        applyChunk(data);
        return true;
      }
    };

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split(/\r?\n\r?\n/);
        buffer = parts.pop();

        for (const part of parts) {
          if (!part.trim()) continue;
          const cont = parseEvent(part);
          if (!cont) {
            buffer = "";
            try {
              await reader.cancel();
            } catch {}
            break;
          }
        }
      }
    } catch (err) {
      if (err.name === "AbortError") throw err;
      console.warn("stream error", err);
    }

    // leftover buffer
    if (buffer.trim()) parseEvent(buffer.trim());

    // finalize
    if (finalSessionId) this.sessionId = finalSessionId;

    // ensure final render is clean markdown
    safeRender(accumulated);

    this.responseCache.set(cacheKey, accumulated);

    return {
      reply: accumulated,
      structural_data,
      session_id: this.sessionId,
    };
  }

  /**
   * sendMessage - UI flow: create user bubble, request streaming response, handle structured_data
   */
  async sendMessage() {
    const message = this.chatInput?.value?.trim();
    if (!message || this.isAITyping) return;

    // Add user bubble
    this.addMessage(this.escapeHtml(message), "user");
    // clear input
    if (this.chatInput) {
      this.chatInput.value = "";
      this.chatInput.style.height = "auto";
    }

    if (!this.rememberMode) {
      this.conversationHistory.push({ role: "user", content: message });
    }

    this.setInputDisabled(true);
    this.showTypingIndicator();

    try {
      const response = await this.getAIResponse(message);
      // hide typing indicator once we have at least processed stream (getAIResponse does streaming updates)
      this.hideTypingIndicator();

      // If server returned structural_data, process them
      let productList = [];
      if (
        response.structural_data &&
        Array.isArray(response.structural_data) &&
        response.structural_data.length > 0
      ) {
        response.structural_data.forEach((data) => {
          if (!data || !data.type) return;
          if (data.type === "Product") productList.push(data);
          else if (data.type === "Cart") this.addCartFromResponse(data);
          else if (data.type === "Order") this.addOrderFromResponse(data);
        });

        if (productList.length > 0) this.addProductsFromResponse(productList);
      }

      // Optionally show final bot bubble if server didn't stream textual reply into a bubble
      // (getAIResponse already created a bot bubble and updated it)
      // but if you want to ensure a final textual bot message also exists in message list, do:
      if (typeof response.reply === "string" && response.reply.trim()) {
        // Already rendered in streaming bubble; nothing more to do.
      }
    } catch (error) {
      this.hideTypingIndicator();
      // If aborted by user, show message
      if (error && error.name === "AbortError") {
        this.addSystemMessage("Stream aborted.");
      } else {
        this.handleError(error);
      }
    } finally {
      this.setInputDisabled(false);
    }
  }

  // Basic markdown renderer (keeps same behavior as your original function)
  renderMarkdown(text) {
    if (!text) return "";
    let html = text;

    // store fenced code blocks
    const codeBlocks = [];
    const inlineCodes = [];

    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
      const idx = codeBlocks.length;
      codeBlocks.push(
        `<pre><code${lang ? ` class="language-${lang}"` : ""}>${this.escapeHtml(code.trim())}</code></pre>`,
      );
      return `__CODE_BLOCK_${idx}__`;
    });

    html = html.replace(/`([^`]+)`/g, (m, code) => {
      const idx = inlineCodes.length;
      inlineCodes.push(`<code>${this.escapeHtml(code)}</code>`);
      return `__INLINE_CODE_${idx}__`;
    });

    html = html.replace(/^---+$/gm, "<hr>");
    html = html.replace(
      /^(#{1,6})\s+(.+)$/gm,
      (m, hashes, txt) =>
        `<h${hashes.length}>${txt.trim()}</h${hashes.length}>`,
    );
    html = html.replace(/^>\s*(.+)$/gm, "<blockquote>$1</blockquote>");
    html = html.replace(
      /^\|(.+)\|\s*\n\|([:\-\s\|]+)\|\s*\n((?:\|.+\|\s*\n?)*)/gm,
      (m, header, sep, rows) => {
        const headerCells = header
          .split("|")
          .map((h) => `<th>${h.trim()}</th>`)
          .join("");
        const rowsHtml = rows
          .trim()
          .split("\n")
          .map((row) => {
            const cells = row
              .split("|")
              .slice(1, -1)
              .map((cell) => `<td>${cell.trim()}</td>`)
              .join("");
            return `<tr>${cells}</tr>`;
          })
          .join("");
        return `<table><thead><tr>${headerCells}</tr></thead><tbody>${rowsHtml}</tbody></table>`;
      },
    );

    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/__(.*?)__/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    html = html.replace(/_([^_]+)_/g, "<em>$1</em>");

    const lines = html.split("\n");
    const processed = [];
    let inList = false,
      listType = null,
      items = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      const orderedMatch = line.match(/^(\d+)\.\s+(.+)/);
      const unorderedMatch = line.match(/^[\-\*\+]\s+(.+)/);
      if (orderedMatch) {
        if (!inList || listType !== "ol") {
          if (inList) {
            processed.push(`</${listType}>`);
          }
          listType = "ol";
          inList = true;
          items = [];
        }
        items.push(`<li>${orderedMatch[2]}</li>`);
      } else if (unorderedMatch) {
        if (!inList || listType !== "ul") {
          if (inList) {
            processed.push(`</${listType}>`);
          }
          listType = "ul";
          inList = true;
          items = [];
        }
        items.push(`<li>${unorderedMatch[1]}</li>`);
      } else {
        if (inList) {
          processed.push(`<${listType}>`);
          processed.push(...items);
          processed.push(`</${listType}>`);
          inList = false;
          listType = null;
          items = [];
        }
        processed.push(line);
      }
    }
    if (inList) {
      processed.push(`<${listType}>`);
      processed.push(...items);
      processed.push(`</${listType}>`);
    }

    html = processed.join("\n");
    html = html.replace(/\n\s*\n/g, "</p><p>");
    const blockElements = /^(<h[1-6]|<hr|<blockquote|<table|<[uo]l|<pre)/;
    if (html.trim() && !blockElements.test(html.trim())) {
      html = `<p>${html}</p>`;
    }
    html = html.replace(/\n/g, "<br>");
    codeBlocks.forEach((c, idx) => {
      html = html.replace(`__CODE_BLOCK_${idx}__`, c);
    });
    inlineCodes.forEach((c, idx) => {
      html = html.replace(`__INLINE_CODE_${idx}__`, c);
    });
    return html;
  }
}

// auto-init if DOM ready
document.addEventListener("DOMContentLoaded", () => {
  window.chatBotService = new ChatBotService();
});
