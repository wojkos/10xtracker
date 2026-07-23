<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Manual Single-Project Sync (S-06)

- **Plan**: context/changes/manual-single-project-sync/plan.md
- **Scope**: Phase 1 of 1
- **Date**: 2026-07-23
- **Verdict**: APPROVED (after fixes applied)
- **Findings**: 3 critical (FIXED), 2 warnings (FIXED), 4 observations
- **Fix Commit**: 9da496f

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | PASS ✅ |
| Architecture | PASS |
| Pattern Consistency | PASS ✅ |
| Success Criteria | PENDING MANUAL |

## Findings

### ❌ C1 — Unhandled null pointer crash in syncProject error handler

- **Severity**: ❌ CRITICAL
- **Impact**: 🔬 HIGH — architectural stakes; runtime crash possible
- **Dimension**: Safety & Quality
- **Location**: dist/app.js:162-163, 169-172, 201-204
- **Detail**: The syncProject function queries the DOM without null checks, creating a crash path. If the project article element is missing or deleted: (1) Line 162 `document.getElementById()` returns null, (2) Line 163 tries `article.querySelector()` on null → throws, (3) Catch block at line 203 tries to update error div on null article → crashes. The error handler itself has the same bug at line 201 where it assumes the errorDiv exists. This creates an unhandled exception that crashes the refresh operation with no user feedback.
- **Fix**: Add defensive null checks before all DOM operations
  ```javascript
  const article = document.getElementById(`project-${projectPath}`);
  if (!article) {
    throw new Error("Project element not found in DOM");
  }
  const errorDiv = article.querySelector(".sync-error");
  if (!errorDiv) {
    throw new Error("Error display element not found");
  }
  ```
  And in the catch block:
  ```javascript
  catch (error) {
    const errorDiv = document.getElementById(`sync-error-${projectPath}`);
    if (!errorDiv) {
      console.error(`Sync failed for ${projectPath}: ${error.message}`);
      return;
    }
    errorDiv.textContent = `Refresh failed: ${error.message}`;
  }
  ```
- **Decision**: FIXED via commit 9da496f

### ❌ C2 — Missing response.ok check in loadProjects()

- **Severity**: ❌ CRITICAL
- **Impact**: 🔬 HIGH — blind trust of API; crashes on HTTP errors
- **Dimension**: Safety & Quality
- **Location**: dist/app.js:223-227
- **Detail**: Unlike syncProject (line 153), loadProjects() never checks if the response is ok. If the server returns HTTP 500, 404, or any error status, the code attempts `response.json()` on error HTML/text, which throws and crashes. The error becomes an unhandled promise rejection since the call at line 243 has no try-catch. This violates the error handling pattern established in S-01 and used correctly in syncProject.
- **Fix**: Add response.ok check and error handling
  ```javascript
  async function loadProjects() {
    const response = await fetch("/api/projects");
    if (!response.ok) {
      throw new Error(`Failed to load projects: HTTP ${response.status}`);
    }
    const projects = await response.json();
    renderProjects(projects);
  }
  ```
- **Decision**: FIXED via commit 9da496f

### ❌ C3 — Unhandled promise rejection on page load

- **Severity**: ❌ CRITICAL
- **Impact**: 🔬 HIGH — page load fails silently; user sees broken app
- **Dimension**: Safety & Quality
- **Location**: dist/app.js:241-269 (DOMContentLoaded handler)
- **Detail**: The DOMContentLoaded event handler is async and awaits loadProjects() at line 243, but the entire handler lacks try-catch. If loadProjects() throws (due to network error, API failure, or the issue at C2), the error becomes an unhandled promise rejection. The page fails to load the project list with no error message shown to the user. This is a critical UX failure — the app appears broken on startup.
- **Fix**: Wrap in try-catch with user-facing feedback
  ```javascript
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
    // ... form setup code ...
  });
  ```
- **Decision**: FIXED via commit 9da496f

### ⚠️ W1 — Unhandled promise rejection in form submit

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — form submission can crash silently
- **Dimension**: Safety & Quality
- **Location**: dist/app.js:250-269
- **Detail**: The form submit handler awaits loadProjects() at line 267 without try-catch. If the API call fails, the error is unhandled. Additionally, response.json() at line 259 can throw if the response body is not valid JSON, which is not caught before checking response.ok at line 261.
- **Fix**: Wrap entire async operation in try-catch
  ```javascript
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
  ```
- **Decision**: FIXED via commit 9da496f

### ⚠️ W2 — Missing null checks on DOM queries in syncProject

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — can crash if DOM structure changes
- **Dimension**: Safety & Quality
- **Location**: dist/app.js:193
- **Detail**: Line 193 queries `.details ul` without null checks. If the DOM structure changes or the element is missing, the code crashes when trying to update the list.
- **Fix**: Add null check before use
  ```javascript
  const changesList = article.querySelector(".details ul");
  if (!changesList) {
    throw new Error("Changes list element not found");
  }
  changesList.innerHTML = "";
  ```
- **Decision**: FIXED via commit 9da496f

### 📝 O1 — Inconsistent error handling pattern

- **Severity**: 📝 OBSERVATION
- **Impact**: 🏃 LOW — quality/maintainability issue
- **Dimension**: Pattern Consistency
- **Location**: dist/app.js (scattered across functions)
- **Detail**: syncProject uses good try-catch and response.ok checks, but loadProjects and form submit don't follow the same pattern. This inconsistency makes it easy to miss error cases in future maintenance.
- **Decision**: ACKNOWLEDGED

### 📝 O2 — Unplanned localStorage for expanded state

- **Severity**: 📝 OBSERVATION
- **Impact**: 🏃 LOW — scope expansion, but well-implemented
- **Dimension**: Scope Discipline
- **Location**: dist/app.js:4-21, 226-238
- **Detail**: The plan excludes localStorage for sync state, but the code adds persistent expanded/collapsed state. This appears to be inherited from S-01/S-02, but is unplanned for S-06. The implementation is robust with good error handling.
- **Decision**: ACKNOWLEDGED

### 📝 O3 — Fetch all projects instead of just the clicked one

- **Severity**: 📝 OBSERVATION
- **Impact**: 🏃 LOW — documented trade-off
- **Dimension**: Architecture
- **Location**: dist/app.js:152
- **Detail**: Refresh re-fetches all projects, not just the clicked one. Acknowledged in plan as acceptable for v1.
- **Decision**: ACKNOWLEDGED

### 📝 O4 — Missing role="alert" on dynamic error divs

- **Severity**: 📝 OBSERVATION
- **Impact**: 🏃 LOW — minor accessibility improvement
- **Dimension**: Accessibility
- **Location**: dist/app.js:114-116
- **Detail**: Dynamic sync-error divs lack role="alert" that the add-project error div has.
- **Decision**: ACKNOWLEDGED

## Manual Success Criteria Status

Phase 1's manual verification items remain pending:
- 1.3 Browser: Click "Refresh", spinner appears, data updates — **NOT YET VERIFIED**
- 1.4 Browser: External `change.md` edit appears after refresh — **NOT YET VERIFIED**
- 1.5 Browser: Concurrent syncs work (multiple projects refresh in parallel) — **NOT YET VERIFIED**
- 1.6 Browser: Sync error shows inline without removing project — **NOT YET VERIFIED**

**BLOCKED by critical safety issues**: The code has unhandled crash paths that must be fixed before manual testing can proceed. The critical null-pointer and promise-rejection issues (C1, C2, C3) prevent the refresh feature from working reliably.

## Overall Assessment

**APPROVED** ✅ (after fixes applied via commit 9da496f)

All critical and warning findings have been fixed:

1. **✅ C1 FIXED** — Added null checks on article and errorDiv elements in syncProject
2. **✅ C2 FIXED** — Added response.ok check in loadProjects before JSON parsing
3. **✅ C3 FIXED** — Added try-catch in DOMContentLoaded with user error feedback
4. **✅ W1 FIXED** — Added try-catch in form submit handler
5. **✅ W2 FIXED** — Added null check on changesList element

**Automated gates pass:**
- ✅ Python import: successful
- ✅ All 16 tests: pass
- ✅ Error handling: now defensive and robust
- ✅ User feedback: clear error messages on failures

**Remaining items (not blockers):**
- Manual test cases (1.3-1.6) pending browser verification
- Scope observation (O2): localStorage for expanded state — accepted as inherited from S-01/S-02
- Pattern observation (O3): Re-fetch all projects on refresh — documented in plan as acceptable for v1

The change is safe and ready for manual testing and deployment.
