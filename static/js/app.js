document.addEventListener("DOMContentLoaded", () => {
  const modeSelect = document.getElementById("modeSelect");
  const algorithmSelect = document.getElementById("algorithmSelect");
  const keyInput = document.getElementById("keyInput");
  const inputText = document.getElementById("inputText");
  const outputText = document.getElementById("outputText");
  const uploadBtn = document.getElementById("uploadBtn");
  const fileInput = document.getElementById("fileInput");
  const downloadBtn = document.getElementById("downloadBtn");
  const runBtn = document.getElementById("runBtn");
  const clearBtn = document.getElementById("clearBtn");
  const logContainer = document.getElementById("logContainer");
  const toastContainer = document.getElementById("toastContainer");
  const statusPill = document.getElementById("statusPill");
  const runSpinner = document.getElementById("runSpinner");

  function updateKeyState() {
    const mode = modeSelect.value;
    const isAnalysis = mode === "Frequency Analysis";
    keyInput.disabled = isAnalysis;
    if (isAnalysis) {
      keyInput.value = "";
    }
  }

  updateKeyState();

  modeSelect.addEventListener("change", () => {
    updateKeyState();
    appendLog(
      `Mode changed to <strong>${modeSelect.value}</strong>.`,
      "info"
    );
  });

  algorithmSelect.addEventListener("change", () => {
    appendLog(
      `Algorithm changed to <strong>${algorithmSelect.value}</strong>.`,
      "info"
    );
  });

  uploadBtn.addEventListener("click", () => {
    fileInput.click();
  });

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".txt")) {
      showToast("Only .txt files are allowed.", "error");
      appendLog("Error: Upload rejected, only .txt allowed.", "error");
      fileInput.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      inputText.value = reader.result;
      appendLog(
        `Loaded input from file <strong>${file.name}</strong>.`,
        "info"
      );
    };
    reader.onerror = () => {
      showToast("Failed to read the text file.", "error");
      appendLog("Error: Failed to read uploaded file.", "error");
    };
    reader.readAsText(file, "utf-8");
  });

  clearBtn.addEventListener("click", () => {
    inputText.value = "";
    outputText.value = "";
    clearLogs();
    appendLog("Cleared input, output and log.", "info");
    keyInput.value = "";
  });

  downloadBtn.addEventListener("click", () => {
    const content = outputText.value || "";
    if (!content) {
      showToast("Nothing to download. Output is empty.", "error");
      appendLog("Error: Download attempted with empty output.", "error");
      return;
    }

    // Use a simple client-side download without extra round trip
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const timestamp = new Date()
      .toISOString()
      .replaceAll(":", "-")
      .replaceAll(".", "-");
    a.href = url;
    a.download = `cipher_output_${timestamp}.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    appendLog("Downloaded current output as text file.", "info");
  });

  runBtn.addEventListener("click", async () => {
    const mode = modeSelect.value;
    const algorithm = algorithmSelect.value;
    const key = keyInput.value.trim();
    const text = inputText.value || "";

    if (!text) {
      showToast("Please enter or upload some input text first.", "error");
      appendLog("Error: Run requested with empty input.", "error");
      return;
    }

    if ((mode === "Encryption" || mode === "Decryption") && !key) {
      showToast("Security key is required for this mode.", "error");
      appendLog(
        "Error: Security key is required for encryption/decryption.",
        "error"
      );
      return;
    }

    setProcessing(true);
    appendLog(
      `Running <strong>${mode}</strong> with <strong>${algorithm}</strong>...`,
      "info"
    );

    try {
      const response = await fetch("/process", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          mode,
          algorithm,
          key: key || null,
          text,
        }),
      });

      const data = await response.json();

      if (!data.success) {
        const msg = data.error || "Processing failed.";
        showToast(msg, "error");
        appendLog(msg, "error");
        if (Array.isArray(data.log)) {
          data.log.forEach((l) => appendLog(l, "error"));
        }
        setStatus("Error", "error");
        return;
      }

      outputText.value = data.result || "";

      if (Array.isArray(data.log)) {
        data.log.forEach((l) => appendLog(l, "info"));
      }

      if (mode === "Frequency Analysis") {
        if (typeof data.detected_key === "number") {
          appendLog(
            `Detected key from analysis: <strong>${data.detected_key}</strong>.`,
            "info"
          );
        }
        if (Array.isArray(data.correlations)) {
          const corrSummary = data.correlations
            .slice(0, 5)
            .map(
              (c) =>
                `k=${c.shift}: ${Number(c.correlation).toFixed(4)}`
            )
            .join(" | ");
          appendLog(
            `Top correlation samples (first 5 shifts): ${corrSummary}`,
            "info"
          );
        }
      }

      showToast("Processing completed successfully.", "success");
      setStatus("Completed", "success");
    } catch (err) {
      console.error(err);
      showToast("Unexpected error during processing.", "error");
      appendLog("Unexpected error during processing.", "error");
      setStatus("Error", "error");
    } finally {
      setProcessing(false);
    }
  });

  function setProcessing(isProcessing) {
    runBtn.disabled = isProcessing;
    modeSelect.disabled = isProcessing;
    algorithmSelect.disabled = isProcessing;
    keyInput.disabled =
      isProcessing || modeSelect.value === "Frequency Analysis";
    uploadBtn.disabled = isProcessing;
    clearBtn.disabled = isProcessing;
    downloadBtn.disabled = isProcessing;

    if (isProcessing) {
      runSpinner.classList.remove("hidden");
      setStatus("Processing...", "processing");
    } else {
      runSpinner.classList.add("hidden");
      if (!statusPill.classList.contains("error")) {
        setStatus("Idle", "idle");
      }
    }
  }

  function setStatus(text, type) {
    statusPill.textContent = text;
    statusPill.classList.remove("processing", "error");
    if (type === "processing") {
      statusPill.classList.add("processing");
    } else if (type === "error") {
      statusPill.classList.add("error");
    }
  }

  function appendLog(message, level) {
    const div = document.createElement("div");
    div.className = "log-entry";
    if (level === "error") {
      div.classList.add("error");
    }
    div.innerHTML = `• ${message}`;
    logContainer.appendChild(div);
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  function clearLogs() {
    logContainer.innerHTML = "";
  }

  function showToast(message, type = "error") {
    const toast = document.createElement("div");
    toast.className = "toast " + (type === "success" ? "toast-success" : "toast-error");
    const iconSpan = document.createElement("span");
    iconSpan.className = "toast-icon";
    iconSpan.textContent = type === "success" ? "✔" : "⚠";
    const msgDiv = document.createElement("div");
    msgDiv.className = "toast-message";
    msgDiv.textContent = message;
    const closeSpan = document.createElement("span");
    closeSpan.className = "toast-close";
    closeSpan.textContent = "✕";
    closeSpan.addEventListener("click", () => {
      toast.remove();
    });
    toast.appendChild(iconSpan);
    toast.appendChild(msgDiv);
    toast.appendChild(closeSpan);
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 4000);
  }
});

