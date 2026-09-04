const loadingProjects = new Set();
let expandedState = {};
let autosyncTimerId = null;
let syncingAll = false;

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

function formatPhaseProgress(phaseProgress) {
  if (!phaseProgress) return "";
  return ` — Phase ${phaseProgress.phase_number}: ${phaseProgress.done}/${phaseProgress.total}`;
}

function formatRoadmapCorrelation(roadmapCorrelation) {
  if (!roadmapCorrelation) return "";
  return ` — ${roadmapCorrelation.roadmap_id}: ${roadmapCorrelation.outcome}`;
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

function renderSummaryStats(aggregates) {
  const countStr = `${aggregates.new} New, ${aggregates.in_progress} In Progress, ${aggregates.done} Done`;

  const summaryStats = document.createElement("p");
  summaryStats.className = "summary-stats aggregate-stats";
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

  return summaryStats;
}

function renderChangeItem(change) {
  const item = document.createElement("li");
  if (change.error) {
    item.textContent = `${change.change_id}: error — ${change.error}`;
    return item;
  }

  const headline = document.createElement("div");
  const idSpan = document.createElement("strong");
  idSpan.textContent = change.change_id;
  headline.appendChild(idSpan);
  headline.appendChild(document.createTextNode(` [${change.status}]${formatPhaseProgress(change.phase_progress)}`));
  item.appendChild(headline);

  const dateSpan = document.createElement("span");
  dateSpan.className = "change-date";
  dateSpan.textContent = change.updated;
  item.appendChild(dateSpan);

  const desc = document.createElement("div");
  desc.className = "change-desc";
  desc.textContent = change.title;
  item.appendChild(desc);

  const roadmap = formatRoadmapCorrelation(change.roadmap_correlation);
  if (roadmap) {
    const roadmapSpan = document.createElement("div");
    roadmapSpan.className = "change-roadmap";
    roadmapSpan.textContent = roadmap.replace(/^ — /, "");
    item.appendChild(roadmapSpan);
  }

  return item;
}

function renderProjectSection(project) {
  const article = document.createElement("article");
  article.setAttribute("data-project-path", project.path);
  article.id = `project-${project.path}`;

  const header = document.createElement("header");

  const heading = document.createElement("h2");
  heading.textContent = project.name;
  header.appendChild(heading);

  const projectPath = document.createElement("p");
  projectPath.className = "summary-stats project-path";
  projectPath.textContent = project.path;
  header.appendChild(projectPath);

  const aggregates = project.aggregates || { new: 0, in_progress: 0, done: 0, blocked: 0 };
  header.appendChild(renderSummaryStats(aggregates));

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

  const removeBtn = document.createElement("button");
  removeBtn.className = "remove-btn";
  removeBtn.textContent = "Remove";
  removeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    removeProject(project.path);
  });
  controls.appendChild(removeBtn);

  header.appendChild(controls);
  article.appendChild(header);

  const details = document.createElement("div");
  details.className = "details";
  details.hidden = true;

  const list = document.createElement("ul");
  for (const change of project.changes) {
    list.appendChild(renderChangeItem(change));
  }
  details.appendChild(list);

  const errorDiv = document.createElement("div");
  errorDiv.className = "sync-error";
  errorDiv.id = `sync-error-${project.path}`;
  details.appendChild(errorDiv);

  article.appendChild(details);

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
    if (!article) {
      throw new Error("Project element not found in DOM");
    }
    const errorDiv = article.querySelector(".sync-error");
    if (!errorDiv) {
      throw new Error("Error display element not found");
    }
    errorDiv.textContent = "";

    project.aggregates = getAggregates(project.changes);

    const header = article.querySelector("header");
    const oldStats = header.querySelector(".aggregate-stats");
    oldStats.replaceWith(renderSummaryStats(project.aggregates));

    const changesList = article.querySelector(".details ul");
    if (!changesList) {
      throw new Error("Changes list element not found");
    }
    changesList.innerHTML = "";
    for (const change of project.changes) {
      changesList.appendChild(renderChangeItem(change));
    }

    const latestDate = project.changes
      .filter(c => !c.error && c.updated)
      .map(c => c.updated)
      .sort()
      .at(-1) ?? "";
    article.dataset.latestChange = latestDate;

    return { path: projectPath, success: true };
  } catch (error) {
    const errorDiv = document.getElementById(`sync-error-${projectPath}`);
    if (!errorDiv) {
      console.error(`Sync failed for ${projectPath}: ${error.message}`);
    } else {
      errorDiv.textContent = `Refresh failed: ${error.message}`;
    }
    return { path: projectPath, success: false, error: error.message };
  } finally {
    loadingProjects.delete(projectPath);
    updateProjectUI(projectPath);
  }
}

async function syncAllProjects() {
  if (syncingAll) return;

  const projectElements = document.querySelectorAll("article[data-project-path]");
  const projectPaths = Array.from(projectElements).map(el => el.getAttribute("data-project-path"));

  if (projectPaths.length === 0) {
    const statusEl = document.getElementById("sync-all-status");
    statusEl.textContent = "No projects to sync";
    return;
  }

  syncingAll = true;
  const syncAllBtn = document.getElementById("sync-all-btn");
  syncAllBtn.disabled = true;

  try {
    for (const path of projectPaths) {
      updateProjectUI(path);
    }

    const statusEl = document.getElementById("sync-all-status");
    statusEl.textContent = "";

    const promises = projectPaths.map(path => syncProject(path));
    const results = await Promise.allSettled(promises);

    const successes = results.filter(r => r.status === "fulfilled" && r.value.success).length;
    const failures = results.filter(r => r.status === "fulfilled" && !r.value.success).length;
    const total = projectPaths.length;

    let statusMessage = `Synced ${successes}/${total} projects`;
    if (failures > 0) {
      const failedProjects = results
        .filter(r => r.status === "fulfilled" && !r.value.success)
        .map(r => `${r.value.path}: ${r.value.error}`)
        .join(", ");
      statusMessage += `. Failed: ${failedProjects}`;
    }

    statusEl.textContent = statusMessage;

    const container = document.getElementById("projects");
    const articles = Array.from(container.querySelectorAll("article[data-project-path]"));
    articles.sort((a, b) => (b.dataset.latestChange ?? "").localeCompare(a.dataset.latestChange ?? ""));
    for (const art of articles) {
      container.appendChild(art);
    }
  } finally {
    syncingAll = false;
    syncAllBtn.disabled = false;
    for (const path of projectPaths) {
      updateProjectUI(path);
    }
  }
}

async function removeProject(projectPath) {
  if (!window.confirm(`Remove "${projectPath}" from tracked projects?`)) {
    return;
  }

  const errorDiv = document.getElementById(`sync-error-${projectPath}`);

  try {
    const response = await fetch("/api/projects", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: projectPath }),
    });
    const body = await response.json();

    if (!response.ok) {
      if (errorDiv) {
        errorDiv.textContent = body.detail || "Failed to remove project.";
      }
      return;
    }

    await loadProjects();
    applyExpandedState();
  } catch (error) {
    if (errorDiv) {
      errorDiv.textContent = `Error: ${error.message}`;
    }
  }
}

function updateProjectUI(projectPath) {
  const section = document.getElementById(`project-${projectPath}`);
  if (!section) return;

  const refreshBtn = section.querySelector(".refresh-btn");
  const removeBtn = section.querySelector(".remove-btn");
  const loadingIndicator = section.querySelector(".loading-indicator");

  const isLoading = loadingProjects.has(projectPath);
  refreshBtn.disabled = isLoading || syncingAll;
  removeBtn.disabled = isLoading || syncingAll;
  loadingIndicator.style.display = isLoading ? "inline-block" : "none";
}

async function loadProjects() {
  const response = await fetch("/api/projects");
  if (!response.ok) {
    throw new Error(`Failed to load projects: HTTP ${response.status}`);
  }
  const projects = await response.json();
  renderProjects(projects);
}

function scheduleAutosync(enabled, intervalMinutes) {
  if (autosyncTimerId !== null) {
    clearInterval(autosyncTimerId);
    autosyncTimerId = null;
  }
  if (enabled) {
    autosyncTimerId = setInterval(autosyncAll, intervalMinutes * 60 * 1000);
  }
}

async function autosyncAll() {
  if (syncingAll) return;

  syncingAll = true;
  try {
    const paths = Array.from(document.querySelectorAll("article[data-project-path]")).map(
      (article) => article.getAttribute("data-project-path")
    );
    for (const path of paths) {
      await syncProject(path);
    }
  } finally {
    syncingAll = false;
    for (const article of document.querySelectorAll("article[data-project-path]")) {
      updateProjectUI(article.getAttribute("data-project-path"));
    }
  }
}

async function loadAutosyncSettings() {
  const response = await fetch("/api/settings");
  if (!response.ok) {
    throw new Error(`Failed to load settings: HTTP ${response.status}`);
  }
  const { enabled, interval_minutes } = await response.json();
  document.getElementById("autosync-enabled").checked = enabled;
  document.getElementById("autosync-interval").value = interval_minutes;
  scheduleAutosync(enabled, interval_minutes);
}

async function saveAutosyncSettings(enabled, intervalMinutes) {
  const errorEl = document.getElementById("autosync-error");
  try {
    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled, interval_minutes: intervalMinutes }),
    });
    const body = await response.json();

    if (!response.ok) {
      errorEl.textContent = body.detail || "Failed to save autosync settings.";
      return;
    }

    errorEl.textContent = "";
    scheduleAutosync(enabled, intervalMinutes);
  } catch (error) {
    errorEl.textContent = `Error: ${error.message}`;
  }
}

function applyExpandedState() {
  for (const article of document.querySelectorAll("article[data-project-path]")) {
    const path = article.getAttribute("data-project-path");
    const details = article.querySelector(".details");
    if (expandedState[path]) {
      details.hidden = false;
    } else {
      details.hidden = true;
    }
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  loadExpandedState();
  try {
    await loadProjects();
    applyExpandedState();
  } catch (error) {
    console.error("Failed to load projects:", error);
    const projectsContainer = document.getElementById("projects");
    projectsContainer.innerHTML =
      '<p style="color: red;">Failed to load projects. Please refresh the page.</p>';
  }

  const syncAllBtn = document.getElementById("sync-all-btn");
  syncAllBtn.addEventListener("click", syncAllProjects);

  const form = document.getElementById("add-project-form");
  const input = document.getElementById("project-path");
  const errorEl = document.getElementById("add-project-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorEl.textContent = "";

    try {
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
      applyExpandedState();
    } catch (error) {
      errorEl.textContent = `Error: ${error.message}`;
    }
  });

  const autosyncEnabledEl = document.getElementById("autosync-enabled");
  const autosyncIntervalEl = document.getElementById("autosync-interval");
  const autosyncErrorEl = document.getElementById("autosync-error");

  function handleAutosyncControlChange() {
    const enabled = autosyncEnabledEl.checked;
    const intervalMinutes = Number(autosyncIntervalEl.value);

    if (!Number.isInteger(intervalMinutes) || intervalMinutes < 1 || intervalMinutes > 1440) {
      autosyncErrorEl.textContent = "Interval must be a whole number between 1 and 1440 minutes.";
      return;
    }

    autosyncErrorEl.textContent = "";
    saveAutosyncSettings(enabled, intervalMinutes);
  }

  autosyncEnabledEl.addEventListener("change", handleAutosyncControlChange);
  autosyncIntervalEl.addEventListener("change", handleAutosyncControlChange);

  try {
    await loadAutosyncSettings();
  } catch (error) {
    console.error("Failed to load autosync settings:", error);
  }
});
