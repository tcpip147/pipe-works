let displayedProcesses = [];
const MAX_LOG_LINES = 500;

function escapeHtml(value) {
  return String(value).replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[character],
  );
}

function toBoolean(value) {
  return value === true || value === 1 || value === "1";
}

function normalizeProcess(process) {
  const statistics = process.statistics || {};

  return {
    name: process.name || process.id,
    pid: process.pid,
    gpu: process.gpu ?? process.inference_gpuid ?? 0,
    frameType: process.frameType || process.inference_frame_type || "pytorch",
    input: process.input || process.input_rtsp_url || "",
    inputState:
      process.inputState || process.input_state || process.desired_state,
    output: process.output || process.output_rtsp_url || "",
    outputState:
      process.outputState || process.output_state || process.desired_state,
    state: process.state || process.desired_state || "stopped",
    statistics: {
      received: statistics.received ?? process.received_frame_count ?? 0,
      sent: statistics.sent ?? process.sent_frame_count ?? 0,
      anomalous: statistics.anomalous ?? process.anomalous_frame_count ?? 0,
      inferenceFailed:
        statistics.inferenceFailed ??
        process.inference_failure_frame_count ??
        0,
      postprocessFailed:
        statistics.postprocessFailed ??
        process.postprocess_failure_frame_count ??
        0,
    },
    config: {
      inputUrl: process.input_rtsp_url,
      inputTransport: process.input_transport,
      jitterBuffer: process.input_jitter_buffer,
      outputUrl: process.output_rtsp_url,
      outputTransport: process.output_transport,
      metadataEnabled: toBoolean(process.metadata_enabled),
      metadataModule: process.metadata_module_path,
      inferenceEnabled: toBoolean(process.inference_enabled),
      intervalFrames: process.inference_interval_frames,
      inputFormat: process.inference_input_format,
      inferenceModule: process.inference_module_path,
      postprocessEnabled: toBoolean(process.postprocess_enabled),
      postprocessModule: process.postprocess_module_path,
      desiredState: process.desired_state === "running",
    },
  };
}

function renderProcesses(processes) {
  const container = document.querySelector("#process-list");
  if (!container) return;
  displayedProcesses = processes.map(normalizeProcess);
  if (displayedProcesses.length === 0) {
    container.classList.add("is-empty");
    container.innerHTML =
      '<p class="empty-state">등록된 프로세스가 없습니다.</p>';
    return;
  }

  container.classList.remove("is-empty");
  container.innerHTML = displayedProcesses
    .map((process, index) => {
      const running = process.state === "running";
      const name = escapeHtml(process.name);
      const details = process.pid
        ? `PID ${process.pid} · GPU ${process.gpu} · ${process.frameType}`
        : `Not started · GPU ${process.gpu} · ${process.frameType}`;
      const deleteAction = running
        ? ""
        : `<button class="context-delete-button" type="button" role="menuitem" data-process-index="${index}">삭제</button>`;
      const actions = `<button class="start-button" type="button" data-process-index="${index}" title="Start ${name}">▶</button><button class="danger-button" type="button" data-process-index="${index}" title="Stop ${name}">■</button><div class="process-menu-container"><button class="more-button" type="button" data-process-index="${index}" aria-haspopup="menu" aria-expanded="false" title="${name} 메뉴">…</button><div class="process-context-menu" role="menu" hidden><button class="context-edit-button" type="button" role="menuitem" data-process-index="${index}">편집</button>${deleteAction}</div></div>`;
      const statistics = process.statistics || {};
      const count = (field) => Number(statistics[field] || 0).toLocaleString();
      return `<article class="process-card ${running ? "is-running" : "is-stopped"}"><div class="process-identity"><span class="process-icon" aria-hidden="true">${running ? "▶" : "■"}</span><div><h3>${name}</h3><p>${escapeHtml(details)}</p></div></div><div class="process-route"><span class="endpoint ${process.inputState === "running" ? "is-running" : ""}">${escapeHtml(process.input)}</span><span aria-hidden="true">→</span><span class="endpoint ${process.outputState === "running" ? "is-running" : ""}">${escapeHtml(process.output)}</span></div><div class="process-actions">${actions}</div><dl class="process-statistics"><div><dt>수신</dt><dd>${count("received")}</dd></div><div><dt>송출</dt><dd>${count("sent")}</dd></div><div class="warning"><dt>비정상</dt><dd>${count("anomalous")}</dd></div><div class="failure"><dt>추론 실패</dt><dd>${count("inferenceFailed")}</dd></div><div class="failure"><dt>후처리 실패</dt><dd>${count("postprocessFailed")}</dd></div></dl></article>`;
    })
    .join("");

  container.querySelectorAll(".process-context-menu").forEach((menu, index) => {
    const logButton = document.createElement("button");
    logButton.className = "context-log-button";
    logButton.type = "button";
    logButton.setAttribute("role", "menuitem");
    logButton.dataset.processIndex = String(index);
    logButton.textContent = "로그";
    menu.insertBefore(logButton, menu.querySelector(".context-delete-button"));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const dialog = document.querySelector("#add-process-dialog");
  const form = document.querySelector("#add-process-form");
  const openButton = document.querySelector("#open-add-process");
  const dialogTitle = document.querySelector("#dialog-title");
  const submitButton = document.querySelector("#dialog-submit");
  const nameInput = form?.elements.namedItem("name");
  const formError = document.querySelector("#process-form-error");
  const actionDialog = document.querySelector("#action-confirm-dialog");
  const actionDialogTitle = document.querySelector("#action-confirm-title");
  const actionProcessName = document.querySelector("#action-process-name");
  const actionConfirmMessage = document.querySelector(
    "#action-confirm-message",
  );
  const actionProcessError = document.querySelector("#action-process-error");
  const confirmActionButton = document.querySelector("#confirm-process-action");
  const cancelActionButton = document.querySelector("#cancel-process-action");
  const logDialog = document.querySelector("#process-log-dialog");
  const logDialogTitle = document.querySelector("#process-log-title");
  const logProcessName = document.querySelector("#process-log-process-name");
  const logOutput = document.querySelector("#process-log-output");
  const closeLogButton = document.querySelector("#close-process-logs");
  let saving = false;
  let pendingProcessAction = null;
  let logSocket = null;
  let logLines = [];
  let statusSocket = null;
  let statusReconnectTimer = null;
  function syncInferenceRequired() {
    form.elements.namedItem("inference_module").required =
      form.elements.namedItem("inference_enabled").checked;
  }
  form?.elements.namedItem("inference_enabled")
    .addEventListener("change", syncInferenceRequired);
  const closeButtons = document.querySelectorAll(
    "#close-add-process, #cancel-add-process",
  );

  function setValue(name, value) {
    const field = form?.elements.namedItem(name);
    if (field && value !== undefined) field.value = value;
  }

  function setChecked(name, checked) {
    const field = form?.elements.namedItem(name);
    if (field) field.checked = checked;
  }

  function showAddDialog() {
    form?.reset();
    formError.textContent = "";
    syncInferenceRequired();
    dialogTitle.textContent = "Add Process";
    submitButton.textContent = "추가";
    nameInput.readOnly = false;
    document.querySelectorAll(".module-current").forEach((hint) => {
      hint.hidden = true;
    });
    dialog?.showModal();
  }

  function showEditDialog(process) {
    formError.textContent = "";
    const config = {
      inputTransport: "tcp",
      jitterBuffer: 30,
      outputTransport: "tcp",
      inferenceEnabled: true,
      intervalFrames: 3,
      inputFormat: "native",
      metadataEnabled: true,
      metadataModule: "",
      inferenceModule: "examples/timestamp.py",
      postprocessEnabled: true,
      postprocessModule: "examples/postprocess.py",
      desiredState: false,
      ...process.config,
    };
    dialogTitle.textContent = "Edit Process";
    submitButton.textContent = "저장";
    setValue("name", process.name);
    nameInput.readOnly = true;
    setChecked("desired_state", config.desiredState);
    setValue("input_rtsp_url", config.inputUrl || process.input);
    setValue("input_transport", config.inputTransport || "tcp");
    setValue("jitter_buffer", config.jitterBuffer || 30);
    setValue("output_rtsp_url", config.outputUrl || `rtsp://${process.output}`);
    setValue("output_transport", config.outputTransport || "tcp");
    setChecked("inference_enabled", config.inferenceEnabled ?? true);
    setValue("gpuid", process.gpu);
    setValue("interval_frames", config.intervalFrames || 3);
    setValue("input_format", config.inputFormat || "native");
    setValue("frame_type", process.frameType);
    setChecked("metadata_enabled", config.metadataEnabled ?? true);
    setValue("metadata_module", config.metadataModule);
    setValue("inference_module", config.inferenceModule);
    setChecked("postprocess_enabled", config.postprocessEnabled ?? true);
    setValue("postprocess_module", config.postprocessModule);
    syncInferenceRequired();
    dialog?.showModal();
  }

  function closeProcessMenus(except = null) {
    document.querySelectorAll(".process-context-menu").forEach((menu) => {
      if (menu === except) return;
      menu.hidden = true;
      menu.parentElement
        ?.querySelector(".more-button")
        ?.setAttribute("aria-expanded", "false");
    });
  }

  function connectStatusSocket() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(
      `${protocol}://${window.location.host}/ws/processes/status`,
    );
    statusSocket = socket;
    socket.addEventListener("message", (message) => {
      try {
        const event = JSON.parse(message.data);
        if (event.type === "process_status") {
          refreshProcesses();
        }
      } catch (error) {
        console.error("Invalid process status event", error);
      }
    });
    socket.addEventListener("close", () => {
      if (statusSocket !== socket) return;
      statusReconnectTimer = window.setTimeout(connectStatusSocket, 1000);
    });
  }

  function appendLog(event) {
    if (!logOutput) return;
    const timestamp = event.created_at
      ? new Date(event.created_at * 1000).toLocaleTimeString()
      : new Date().toLocaleTimeString();
    const exception = event.exception ? `\n${event.exception}` : "";
    logLines.push(
      `[${timestamp}] [${event.level || "INFO"}] [${event.logger || "stream"}] ${event.message || ""}${exception}`,
    );
    if (logLines.length > MAX_LOG_LINES) {
      logLines.splice(0, logLines.length - MAX_LOG_LINES);
    }
    logOutput.textContent = `${logLines.join("\n")}\n`;
    logOutput.scrollTop = logOutput.scrollHeight;
  }

  function closeLogDialog() {
    if (logSocket) {
      logSocket.close(1000, "Log dialog closed");
      logSocket = null;
    }
  }

  function showLogDialog(process) {
    closeLogDialog();
    logDialogTitle.textContent = "Logs";
    logProcessName.textContent = process.name;
    logLines = [];
    logOutput.textContent = "Waiting for log messages...\n";
    logDialog?.showModal();

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const processId = encodeURIComponent(process.name);
    logSocket = new WebSocket(
      `${protocol}://${window.location.host}/ws/processes/${processId}/logs`,
    );
    logSocket.addEventListener("message", (message) => {
      try {
        appendLog(JSON.parse(message.data));
      } catch (error) {
        console.error("Invalid process log event", error);
      }
    });
    logSocket.addEventListener("error", () => {
      appendLog({ level: "ERROR", message: "Log connection failed." });
    });
    logSocket.addEventListener("close", (event) => {
      if (!event.wasClean && logDialog?.open) {
        appendLog({ level: "WARNING", message: "Log connection closed." });
      }
    });
  }

  async function deleteProcess(process) {
    const response = await fetch(
      `/api/processes?process_id=${encodeURIComponent(process.name)}`,
      { method: "DELETE" },
    );
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `삭제에 실패했습니다. (${response.status})`);
    }
    await refreshProcesses();
  }

  async function startProcess(process) {
    const response = await fetch(
      `/api/processes/start?process_id=${encodeURIComponent(process.name)}`,
      { method: "POST" },
    );
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `시작에 실패했습니다. (${response.status})`);
    }
  }

  async function stopProcess(process) {
    const response = await fetch(
      `/api/processes/stop?process_id=${encodeURIComponent(process.name)}`,
      { method: "POST" },
    );
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `정지에 실패했습니다. (${response.status})`);
    }
  }

  function showActionDialog(process, action) {
    const labels = {
      start: { title: "프로세스 시작", message: "시작하시겠습니까?", button: "시작" },
      stop: { title: "프로세스 정지", message: "정지하시겠습니까?", button: "정지" },
      delete: { title: "프로세스 삭제", message: "삭제하시겠습니까?", button: "삭제" },
    };
    const label = labels[action];
    pendingProcessAction = { process, action };
    actionDialogTitle.textContent = label.title;
    actionProcessName.textContent = process.name;
    actionConfirmMessage.textContent = label.message;
    confirmActionButton.textContent = label.button;
    confirmActionButton.classList.toggle("delete-confirm-button", action === "delete");
    actionProcessError.textContent = "";
    confirmActionButton.disabled = false;
    actionDialog.showModal();
  }

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (saving) return;
    formError.textContent = "";
    const editing = nameInput.readOnly;
    const process = Object.fromEntries(new FormData(form));
    for (const name of [
      "desired_state",
      "metadata_enabled",
      "inference_enabled",
      "postprocess_enabled",
    ]) {
      process[name] = form.elements.namedItem(name).checked;
    }
    for (const name of ["gpuid", "jitter_buffer", "interval_frames"]) {
      process[name] = Number(process[name]);
    }
    saving = true;
    submitButton.disabled = true;
    openButton.disabled = true;
    try {
      const url = editing
        ? `/api/processes?process_id=${encodeURIComponent(process.name)}`
        : "/api/processes";
      const response = await fetch(url, {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(process),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        const detail = Array.isArray(body.detail)
          ? body.detail.map((item) => `${item.loc.join(".")}: ${item.msg}`).join("\n")
          : body.detail;
        throw new Error(detail || `저장에 실패했습니다. (${response.status})`);
      }
      dialog.close();
      await refreshProcesses();
    } catch (error) {
      formError.textContent = error.message;
    } finally {
      saving = false;
      submitButton.disabled = false;
      openButton.disabled = false;
    }
  });

  openButton?.addEventListener("click", showAddDialog);
  closeButtons.forEach((button) => {
    button.addEventListener("click", () => dialog?.close());
  });

  document
    .querySelector("#process-list")
    ?.addEventListener("click", (event) => {
      const startButton = event.target.closest(".start-button");
      if (startButton) {
        showActionDialog(
          displayedProcesses[Number(startButton.dataset.processIndex)],
          "start",
        );
        return;
      }

      const stopButton = event.target.closest(".danger-button");
      if (stopButton) {
        showActionDialog(
          displayedProcesses[Number(stopButton.dataset.processIndex)],
          "stop",
        );
        return;
      }

      const moreButton = event.target.closest(".more-button");
      if (moreButton) {
        const menu = moreButton.parentElement.querySelector(
          ".process-context-menu",
        );
        const willOpen = menu.hidden;
        closeProcessMenus(menu);
        menu.hidden = !willOpen;
        moreButton.setAttribute("aria-expanded", String(willOpen));
        return;
      }

      const editButton = event.target.closest(".context-edit-button");
      if (editButton) {
        if (saving) return;
        closeProcessMenus();
        showEditDialog(
          displayedProcesses[Number(editButton.dataset.processIndex)],
        );
        return;
      }

      const logButton = event.target.closest(".context-log-button");
      if (logButton) {
        const process = displayedProcesses[Number(logButton.dataset.processIndex)];
        closeProcessMenus();
        showLogDialog(process);
        return;
      }

      const deleteButton = event.target.closest(".context-delete-button");
      if (deleteButton) {
        const process =
          displayedProcesses[Number(deleteButton.dataset.processIndex)];
        closeProcessMenus();
        showActionDialog(process, "delete");
      }
    });

  confirmActionButton?.addEventListener("click", async () => {
    if (!pendingProcessAction || confirmActionButton.disabled) return;
    confirmActionButton.disabled = true;
    actionProcessError.textContent = "";
    try {
      if (pendingProcessAction.action === "start") {
        await startProcess(pendingProcessAction.process);
      } else if (pendingProcessAction.action === "stop") {
        await stopProcess(pendingProcessAction.process);
      } else if (pendingProcessAction.action === "delete") {
        await deleteProcess(pendingProcessAction.process);
      }
      actionDialog.close();
    } catch (error) {
      actionProcessError.textContent = error.message;
      confirmActionButton.disabled = false;
    }
  });

  cancelActionButton?.addEventListener("click", () => actionDialog.close());
  closeLogButton?.addEventListener("click", () => logDialog?.close());
  logDialog?.addEventListener("close", closeLogDialog);
  actionDialog?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      confirmActionButton.click();
    } else if (event.key === "Escape") {
      event.preventDefault();
      actionDialog.close();
    }
  });
  actionDialog?.addEventListener("close", () => {
    pendingProcessAction = null;
    actionProcessError.textContent = "";
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".process-menu-container")) {
      closeProcessMenus();
    }
  });

  async function refreshProcesses() {
    try {
      const response = await fetch("/api/processes");
      if (!response.ok) {
        throw new Error(`process API failed: ${response.status}`);
      }

      const processes = await response.json();
      renderProcesses(Array.isArray(processes) ? processes : []);
    } catch (error) {
      console.error("프로세스 목록을 불러오지 못했습니다.", error);
      renderProcesses([]);
    }
  }

  refreshProcesses();
  connectStatusSocket();
  window.addEventListener("beforeunload", () => {
    if (statusReconnectTimer !== null) {
      window.clearTimeout(statusReconnectTimer);
    }
    statusSocket?.close();
  });
});
