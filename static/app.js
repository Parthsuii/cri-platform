const state = {
  tasks: [],
  latest: null,
  trace: [],
};

const $ = (selector) => document.querySelector(selector);
const canvas = $("#topology-canvas");
const ctx = canvas?.getContext("2d");
const nodes = [];

function pretty(data) {
  return JSON.stringify(data, null, 2);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function setHealth(ok) {
  $("#health-dot").classList.toggle("ok", ok);
  $("#health-label").textContent = ok ? "Online" : "Offline";
}

function updateMetrics() {
  const passed = state.tasks.filter((task) => task.verification?.passed).length;
  const checkpoints = state.tasks.filter((task) => task.checkpoint_id).length;
  $("#metric-tasks").textContent = String(state.tasks.length);
  $("#metric-passed").textContent = String(passed);
  $("#metric-checkpoints").textContent = String(checkpoints);
  $("#metric-trace").textContent = String(state.trace.length);
}

function sizeCanvas() {
  if (!canvas || !ctx) return;
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.floor(window.innerWidth * scale);
  canvas.height = Math.floor(window.innerHeight * scale);
  canvas.style.width = `${window.innerWidth}px`;
  canvas.style.height = `${window.innerHeight}px`;
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  nodes.length = 0;
  const count = Math.max(24, Math.floor(window.innerWidth / 40));
  for (let index = 0; index < count; index += 1) {
    nodes.push({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.42,
      vy: (Math.random() - 0.5) * 0.42,
      r: 1.8 + Math.random() * 2.8,
    });
  }
}

function drawTopology() {
  if (!canvas || !ctx) return;
  ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

  for (const node of nodes) {
    node.x += node.vx;
    node.y += node.vy;
    if (node.x < 0 || node.x > window.innerWidth) node.vx *= -1;
    if (node.y < 0 || node.y > window.innerHeight) node.vy *= -1;
  }

  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const a = nodes[i];
      const b = nodes[j];
      const distance = Math.hypot(a.x - b.x, a.y - b.y);
      if (distance < 190) {
        ctx.strokeStyle = `rgba(45, 212, 191, ${0.14 * (1 - distance / 190)})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }
  }

  for (const node of nodes) {
    const glow = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, node.r * 7);
    glow.addColorStop(0, "rgba(45, 212, 191, 0.65)");
    glow.addColorStop(1, "rgba(45, 212, 191, 0)");
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(node.x, node.y, node.r * 7, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "rgba(221, 247, 255, 0.78)";
    ctx.beginPath();
    ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
    ctx.fill();
  }

  requestAnimationFrame(drawTopology);
}

function summarizeResult(result) {
  const history = result.result?.state?.execution_history || result.result?.execution_history || [];
  const latest = history[history.length - 1];
  return {
    task_id: result.task_id,
    status: result.status,
    mode: result.mode,
    task: result.task,
    checkpoint_id: result.checkpoint_id,
    verification: result.verification,
    route: latest?.output?.route || "n/a",
    stdout: latest?.output?.result?.stdout || "",
    raw: result,
  };
}

function renderTasks() {
  const container = $("#task-list");
  if (!state.tasks.length) {
    container.innerHTML = '<div class="task-row"><small>No tasks submitted yet.</small></div>';
    return;
  }
  container.innerHTML = state.tasks
    .slice()
    .reverse()
    .map((task) => {
      const statusClass = task.status === "completed" ? "ok" : "failed";
      return `
        <button class="task-row" type="button" data-task-id="${task.task_id}">
          <strong>${task.task_id}</strong>
          <small>${task.mode} | ${task.task}</small>
          <span class="badge ${statusClass}">${task.status}</span>
        </button>
      `;
    })
    .join("");
}

function renderK8s(plan) {
  $("#k8s-list").innerHTML = plan.apply_order
    .map(
      (item) => `
        <div class="manifest-row">
          <strong>${item.kind}: ${item.name}</strong>
          <small>${item.path}</small>
        </div>
      `,
    )
    .join("");
}

async function refresh() {
  try {
    await request("/health");
    setHealth(true);
  } catch {
    setHealth(false);
  }

  try {
    state.tasks = await request("/tasks");
    renderTasks();
  } catch {
    state.tasks = [];
  }

  try {
    state.trace = await request("/trace");
    $("#trace-output").textContent = state.trace.length ? pretty(state.trace.slice(-10)) : "No trace events yet.";
  } catch {
    state.trace = [];
  }

  try {
    renderK8s(await request("/k8s/plan"));
  } catch {
    $("#k8s-list").innerHTML = '<div class="manifest-row"><small>Kubernetes plan unavailable.</small></div>';
  }

  try {
    const metrics = await request("/compiler/metrics");
    $("#metric-compilations").textContent = String(metrics.total_compilations);
    $("#metric-comp-success").textContent = `${Math.round(metrics.success_rate * 100)}%`;
  } catch {
    $("#metric-compilations").textContent = "0";
    $("#metric-comp-success").textContent = "100%";
  }

  updateMetrics();
}

async function submitTask(event) {
  event.preventDefault();
  const task = $("#task-input").value.trim();
  const mode = $("#mode-input").value;
  if (!task) return;

  $("#latest-status").textContent = "Running";
  $("#latest-status").className = "badge";
  $("#result-output").textContent = "Executing task...";

  try {
    const result = await request("/tasks", {
      method: "POST",
      body: JSON.stringify({ task, mode }),
    });
    state.latest = result;
    $("#latest-status").textContent = result.status;
    $("#latest-status").className = `badge ${result.status === "completed" ? "ok" : "failed"}`;
    $("#result-output").textContent = pretty(summarizeResult(result));
    $("#checkpoint-input").value = result.checkpoint_id || "";
    await refresh();
  } catch (error) {
    $("#latest-status").textContent = "Failed";
    $("#latest-status").className = "badge failed";
    $("#result-output").textContent = error.message;
  }
}

async function rollback() {
  const checkpointId = $("#checkpoint-input").value.trim();
  if (!checkpointId) return;
  $("#rollback-output").textContent = "Restoring checkpoint...";
  try {
    const result = await request("/rollback", {
      method: "POST",
      body: JSON.stringify({ checkpoint_id: checkpointId }),
    });
    $("#rollback-output").textContent = pretty(result);
  } catch (error) {
    $("#rollback-output").textContent = error.message;
  }
}

async function submitCompiler(event) {
  event.preventDefault();
  const prompt = $("#compiler-input").value.trim();
  if (!prompt) return;

  const steps = [
    { id: "#step-intent" },
    { id: "#step-architecture" },
    { id: "#step-schema" },
    { id: "#step-validation" },
    { id: "#step-repair" },
    { id: "#step-runtime" }
  ];

  // Reset visual steps
  steps.forEach(s => {
    $(s.id).className = "";
  });

  $("#compiler-status").textContent = "Compiling";
  $("#compiler-status").className = "badge";
  $("#compiler-output").textContent = "Compiling requirements into validated application specifications...";
  $("#compiler-output").style.display = "block";
  $("#compiler-results").style.display = "none";

  // Simulate pipeline steps animation
  for (const step of steps) {
    await new Promise(resolve => setTimeout(resolve, 200));
    $(step.id).className = "active";
  }

  try {
    const result = await request("/compiler/compile", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    });

    // Mark steps completed
    steps.forEach(s => {
      $(s.id).className = "active";
    });

    if (result.validation && !result.validation.valid) {
      if (result.repair && result.repair.success) {
        $("#step-repair").className = "active";
      } else {
        $("#step-repair").className = "failed";
      }
    }
    
    if (result.runtime && !result.runtime.passed) {
      $("#step-runtime").className = "failed";
    }

    $("#compiler-status").textContent = result.runtime.passed ? "Success" : "Failed";
    $("#compiler-status").className = `badge ${result.runtime.passed ? "ok" : "failed"}`;

    // Fill tabs content
    $("#out-intent").textContent = pretty(result.intent);
    $("#out-arch").textContent = pretty(result.architecture);
    $("#out-db").textContent = pretty(result.database);
    $("#out-api").textContent = pretty(result.api);
    $("#out-ui").textContent = pretty(result.ui);
    $("#out-auth").textContent = pretty(result.auth);
    $("#out-biz").textContent = pretty(result.business);
    $("#out-val").textContent = pretty(result.validation);
    $("#out-rep").textContent = result.repair ? pretty(result.repair) : "No repair was needed.";
    $("#out-run").textContent = pretty(result.runtime);

    $("#compiler-output").style.display = "none";
    $("#compiler-results").style.display = "block";
    
    await refresh();
  } catch (error) {
    $("#compiler-status").textContent = "Error";
    $("#compiler-status").className = "badge failed";
    $("#compiler-output").textContent = error.message;
    $("#step-runtime").className = "failed";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#task-form").addEventListener("submit", submitTask);
  $("#compiler-form").addEventListener("submit", submitCompiler);
  $("#refresh-button").addEventListener("click", refresh);
  $("#trace-button").addEventListener("click", refresh);
  $("#rollback-button").addEventListener("click", rollback);
  $("#sample-risk").addEventListener("click", () => {
    $("#mode-input").value = "agent";
    $("#task-input").value = "run rm temp.txt";
  });
  $("#task-list").addEventListener("click", (event) => {
    const row = event.target.closest("[data-task-id]");
    if (!row) return;
    const task = state.tasks.find((item) => item.task_id === row.dataset.taskId);
    if (task) {
      $("#latest-status").textContent = task.status;
      $("#latest-status").className = `badge ${task.status === "completed" ? "ok" : "failed"}`;
      $("#result-output").textContent = pretty(summarizeResult(task));
      $("#checkpoint-input").value = task.checkpoint_id || "";
    }
  });

  // Compiler Tabs Click
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      
      const targetTab = btn.dataset.tab;
      document.querySelectorAll(".tab-content").forEach(content => {
        if (content.id === targetTab) {
          content.classList.remove("style-hide");
        } else {
          content.classList.add("style-hide");
        }
      });
    });
  });

  sizeCanvas();
  drawTopology();
  refresh();
});

window.addEventListener("resize", sizeCanvas);
