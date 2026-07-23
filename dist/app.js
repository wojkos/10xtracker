function renderProjects(projects) {
  const container = document.getElementById("projects");
  container.innerHTML = "";

  for (const project of projects) {
    const section = document.createElement("section");

    const heading = document.createElement("h2");
    heading.textContent = `${project.name} (${project.path})`;
    section.appendChild(heading);

    const list = document.createElement("ul");
    for (const change of project.changes) {
      const item = document.createElement("li");
      item.textContent = change.error
        ? `${change.change_id}: error — ${change.error}`
        : `${change.title} [${change.status}] — updated ${change.updated}`;
      list.appendChild(item);
    }
    section.appendChild(list);

    container.appendChild(section);
  }
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
