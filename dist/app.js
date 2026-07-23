const loadingProjects = new Set();
let expandedState = {};

function loadExpandedState() {
  try {
    const saved = localStorage.getItem("expanded_projects");
    expandedState = saved ? JSON.parse(saved) : {};
  } catch {
    expandedState = {};
  }
  return expandedState;
}

function saveExpandedState(state) {
  expandedState = state;
  try {
    localStorage.setItem("expanded_projects", JSON.stringify(state));
  } catch {
    console.error("Failed to save expanded state to localStorage");
  }
}

function getStatusBucket(status) {
  if (status === "new" || status === "preparing") return "new";
  if (status === "planned" || status === "plan_reviewed" || status === "implementing") return "in_progress";
  if (status === "implemented" || status === "impl_reviewed" || status === "archived") return "done";
  if (status === "blocked") return "blocked";
  return "unknown";
}

function getAggregates(changes) {
  const aggregates = { new: 0, in_progress: 0, done: 0, blocked: 0 };
  for (const change of changes) {
    if (change.error) continue;
    const bucket = getStatusBucket(change.status);
    if (bucket in aggregates) {
      aggregates[bucket]++;
    }
  }
  return aggregates;
}

function renderProjectSection(project) {
  const article = document.createElement("article");
  article.setAttribute("data-project-path", project.path);
  article.id = `project-${project.path}`;

  const header = document.createElement("header");

  const heading = document.createElement("h2");
  heading.textContent = `${project.name} (${project.path})`;
  header.appendChild(heading);

  const aggregates = project.aggregates || { new: 0, in_progress: 0, done: 0, blocked: 0 };
  const countStr = `${aggregates.new} New, ${aggregates.in_progress} In Progress, ${aggregates.done} Done`;

  const summaryStats = document.createElement("p");
  summaryStats.className = "summary-stats";
  summaryStats.textContent = countStr;

  if (aggregates.blocked > 0) {
    const blockedNote = document.createElement("span");
    blockedNote.className = "blocked-note";
    blockedNote.textContent = ` (${aggregates.blocked} Blocked)`;
    summaryStats.appendChild(blockedNote);
  }

  const total = aggregates.new + aggregates.in_progress + aggregates.done + aggregates.blocked;
  if (total === 0) {
    const emptyNote = document.createElement("span");
    emptyNote.textContent = " (no readable changes)";
    summaryStats.appendChild(emptyNote);
  }

  header.appendChild(summaryStats);

  const controls = document.createElement("div");
  controls.className = "project-controls";

  const refreshBtn = document.createElement("button");
  refreshBtn.className = "refresh-btn";
  refreshBtn.textContent = "Refresh";
  refreshBtn.disabled = loadingProjects.has(project.path);
  refreshBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    syncProject(project.path);
  });
  controls.appendChild(refreshBtn);

  const loadingIndicator = document.createElement("span");
  loadingIndicator.className = "loading-indicator";
  loadingIndicator.textContent = "Refreshing...";
  loadingIndicator.style.display = loadingProjects.has(project.path) ? "inline-block" : "none";
  controls.appendChild(loadingIndicator);

  header.appendChild(controls);

  header.addEventListener("click", (e) => {
    if (e.target.closest(".project-controls")) {
      return;
    }
    details.hidden = !details.hidden;
    if (details.hidden) {
      delete expandedState[project.path];
    } else {
      expandedState[project.path] = true;
    }
    saveExpandedState(expandedState);
  });

  article.appendChild(header);

  const details = document.createElement("div");
  details.className = "details";
  details.hidden = true;

  const list = document.createElement("ul");
  for (const change of project.changes) {
    const item = document.createElement("li");
    item.textContent = change.error
      ? `${change.change_id}: error — ${change.error}`
      : `${change.title} [${change.status}] — updated ${change.updated}`;
    list.appendChild(item);
  }
  details.appendChild(list);

  const errorDiv = document.createElement("div");
  errorDiv.className = "sync-error";
  errorDiv.id = `sync-error-${project.path}`;
  details.appendChild(errorDiv);

  article.appendChild(details);

  return article;
}

function renderProjects(projects) {
  const container = document.getElementById("projects");
  container.innerHTML = "";

  for (const project of projects) {
    project.aggregates = getAggregates(project.changes);
    const section = renderProjectSection(project);
    container.appendChild(section);
  }
}

async function syncProject(projectPath) {
  loadingProjects.add(projectPath);
  updateProjectUI(projectPath);

  try {
    const response = await fetch("/api/projects");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const projects = await response.json();
    const project = projects.find(p => p.path === projectPath);
    if (!project) {
      throw new Error("Project not found in response");
    }

    const article = document.getElementById(`project-${projectPath}`);
    const errorDiv = article.querySelector(".sync-error");
    errorDiv.textContent = "";

    project.aggregates = getAggregates(project.changes);

    const header = article.querySelector("header");
    const oldStats = header.querySelector(".summary-stats");
    const aggregates = project.aggregates;
    const countStr = `${aggregates.new} New, ${aggregates.in_progress} In Progress, ${aggregates.done} Done`;

    const newStats = document.createElement("p");
    newStats.className = "summary-stats";
    newStats.textContent = countStr;

    if (aggregates.blocked > 0) {
      const blockedNote = document.createElement("span");
      blockedNote.className = "blocked-note";
      blockedNote.textContent = ` (${aggregates.blocked} Blocked)`;
      newStats.appendChild(blockedNote);
    }

    const total = aggregates.new + aggregates.in_progress + aggregates.done + aggregates.blocked;
    if (total === 0) {
      const emptyNote = document.createElement("span");
      emptyNote.textContent = " (no readable changes)";
      newStats.appendChild(emptyNote);
    }

    oldStats.replaceWith(newStats);

    const changesList = article.querySelector(".details ul");
    changesList.innerHTML = "";
    for (const change of project.changes) {
      const item = document.createElement("li");
      item.textContent = change.error
        ? `${change.change_id}: error — ${change.error}`
        : `${change.title} [${change.status}] — updated ${change.updated}`;
      changesList.appendChild(item);
    }
  } catch (error) {
    const errorDiv = document.getElementById(`sync-error-${projectPath}`);
    errorDiv.textContent = `Refresh failed: ${error.message}`;
  } finally {
    loadingProjects.delete(projectPath);
    updateProjectUI(projectPath);
  }
}

function updateProjectUI(projectPath) {
  const section = document.getElementById(`project-${projectPath}`);
  if (!section) return;

  const refreshBtn = section.querySelector(".refresh-btn");
  const loadingIndicator = section.querySelector(".loading-indicator");

  const isLoading = loadingProjects.has(projectPath);
  refreshBtn.disabled = isLoading;
  loadingIndicator.style.display = isLoading ? "inline-block" : "none";
}

async function loadProjects() {
  const response = await fetch("/api/projects");
  const projects = await response.json();
  renderProjects(projects);
}

document.addEventListener("DOMContentLoaded", () => {
  loadProjects();

  const form = document.getElementById("add-project-form");
  const input = document.getElementById("project-path");
  const errorEl = document.getElementById("add-project-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorEl.textContent = "";

    const response = await fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: input.value }),
    });
    const body = await response.json();

    if (!response.ok) {
      errorEl.textContent = body.detail || "Failed to add project.";
      return;
    }

    input.value = "";
    await loadProjects();
  });
});
