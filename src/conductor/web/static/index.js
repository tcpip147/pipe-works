const SAMPLE_PROCESSES = [
  { name: "camera-001", pid: 18420, gpu: 0, frameType: "pytorch", input: "cctv001.stream", inputState: "running", output: "localhost:8554/cctv001", outputState: "running", state: "running", statistics: { received: 128420, sent: 128417, anomalous: 2, inferenceFailed: 1, postprocessFailed: 0 } },
  { name: "camera-002", pid: 19284, gpu: 0, frameType: "pytorch", input: "cctv002.stream", inputState: "running", output: "localhost:8554/cctv002", outputState: "stopped", state: "running", statistics: { received: 84539, sent: 84535, anomalous: 3, inferenceFailed: 0, postprocessFailed: 2 } },
  { name: "parking-lot", pid: null, gpu: 0, frameType: "pytorch", input: "parking.stream", inputState: "stopped", output: "localhost:8554/parking", outputState: "stopped", state: "stopped", statistics: { received: 0, sent: 0, anomalous: 0, inferenceFailed: 0, postprocessFailed: 0 } },
  { name: "parking-lot", pid: null, gpu: 0, frameType: "pytorch", input: "parking.stream", inputState: "stopped", output: "localhost:8554/parking", outputState: "stopped", state: "stopped", statistics: { received: 0, sent: 0, anomalous: 0, inferenceFailed: 0, postprocessFailed: 0 } },
  { name: "parking-lot", pid: null, gpu: 0, frameType: "pytorch", input: "parking.stream", inputState: "stopped", output: "localhost:8554/parking", outputState: "stopped", state: "stopped", statistics: { received: 0, sent: 0, anomalous: 0, inferenceFailed: 0, postprocessFailed: 0 } },
  { name: "parking-lot", pid: null, gpu: 0, frameType: "pytorch", input: "parking.stream", inputState: "stopped", output: "localhost:8554/parking", outputState: "stopped", state: "stopped", statistics: { received: 0, sent: 0, anomalous: 0, inferenceFailed: 0, postprocessFailed: 0 } },
  { name: "parking-lot", pid: null, gpu: 0, frameType: "pytorch", input: "parking.stream", inputState: "stopped", output: "localhost:8554/parking", outputState: "stopped", state: "stopped", statistics: { received: 0, sent: 0, anomalous: 0, inferenceFailed: 0, postprocessFailed: 0 } },
  { name: "parking-lot", pid: null, gpu: 0, frameType: "pytorch", input: "parking.stream", inputState: "stopped", output: "localhost:8554/parking", outputState: "stopped", state: "stopped", statistics: { received: 0, sent: 0, anomalous: 0, inferenceFailed: 0, postprocessFailed: 0 } },
  { name: "parking-lot", pid: null, gpu: 0, frameType: "pytorch", input: "parking.stream", inputState: "stopped", output: "localhost:8554/parking", outputState: "stopped", state: "stopped", statistics: { received: 0, sent: 0, anomalous: 0, inferenceFailed: 0, postprocessFailed: 0 } },
  { name: "parking-lot", pid: null, gpu: 0, frameType: "pytorch", input: "parking.stream", inputState: "stopped", output: "localhost:8554/parking", outputState: "stopped", state: "stopped", statistics: { received: 0, sent: 0, anomalous: 0, inferenceFailed: 0, postprocessFailed: 0 } },
];

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function renderProcesses(processes) {
  const container = document.querySelector("#process-list");
  if (!container) return;
  container.innerHTML = processes.map((process, index) => {
    const running = process.state === "running";
    const name = escapeHtml(process.name);
    const details = process.pid
      ? `PID ${process.pid} · GPU ${process.gpu} · ${process.frameType}`
      : `Not started · GPU ${process.gpu} · ${process.frameType}`;
    const actions = `<button class="start-button" type="button" title="Start ${name}">▶</button><button class="danger-button" type="button" title="Stop ${name}">■</button><button class="edit-button" type="button" data-process-index="${index}" title="Edit ${name}">…</button>`;
    const statistics = process.statistics || {};
    const count = (field) => Number(statistics[field] || 0).toLocaleString();
    return `<article class="process-card ${running ? "is-running" : "is-stopped"}"><div class="process-identity"><span class="process-icon" aria-hidden="true">${running ? "▶" : "■"}</span><div><h3>${name}</h3><p>${escapeHtml(details)}</p></div></div><div class="process-route"><span class="endpoint ${process.inputState === "running" ? "is-running" : ""}">${escapeHtml(process.input)}</span><span aria-hidden="true">→</span><span class="endpoint ${process.outputState === "running" ? "is-running" : ""}">${escapeHtml(process.output)}</span></div><div class="process-actions">${actions}</div><dl class="process-statistics"><div><dt>수신</dt><dd>${count("received")}</dd></div><div><dt>송출</dt><dd>${count("sent")}</dd></div><div class="warning"><dt>비정상</dt><dd>${count("anomalous")}</dd></div><div class="failure"><dt>추론 실패</dt><dd>${count("inferenceFailed")}</dd></div><div class="failure"><dt>후처리 실패</dt><dd>${count("postprocessFailed")}</dd></div></dl></article>`;
  }).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  const dialog = document.querySelector("#add-process-dialog");
  const form = document.querySelector("#add-process-form");
  const openButton = document.querySelector("#open-add-process");
  const dialogTitle = document.querySelector("#dialog-title");
  const submitButton = document.querySelector("#dialog-submit");
  const nameInput = form?.elements.namedItem("name");
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
    dialogTitle.textContent = "Add Process";
    submitButton.textContent = "추가";
    nameInput.readOnly = false;
    document.querySelectorAll(".module-current").forEach((hint) => {
      hint.hidden = true;
    });
    dialog?.showModal();
  }

  function showEditDialog(process) {
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
      ...process.config,
    };
    dialogTitle.textContent = "Edit Process";
    submitButton.textContent = "저장";
    setValue("name", process.name);
    nameInput.readOnly = true;
    setValue("input_rtsp_url", config.inputUrl || `rtsp://${process.input}`);
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
    dialog?.showModal();
  }

  openButton?.addEventListener("click", showAddDialog);
  closeButtons.forEach((button) => {
    button.addEventListener("click", () => dialog?.close());
  });

  document.querySelector("#process-list")?.addEventListener("click", (event) => {
    const editButton = event.target.closest(".edit-button");
    if (editButton) {
      showEditDialog(SAMPLE_PROCESSES[Number(editButton.dataset.processIndex)]);
    }
  });

  renderProcesses(SAMPLE_PROCESSES);
});
