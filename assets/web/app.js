const state = {
  branches: [],
  archivedBranches: [],
  filteredBranches: [],
  projects: [],
  context: null,
  selectedGroupId: "",
  selectedRecordId: "",
  drawerOpen: false,
  projectPanelOpen: false,
  archivePanelOpen: false,
  appendMode: false,
  drawerContext: null,
};

const els = {
  searchInput: document.getElementById("searchInput"),
  projectFilter: document.getElementById("projectFilter"),
  projectPanelButton: document.getElementById("projectPanelButton"),
  archivePanelButton: document.getElementById("archivePanelButton"),
  currentChangeButton: document.getElementById("currentChangeButton"),
  reloadButton: document.getElementById("reloadButton"),
  contextProject: document.getElementById("contextProject"),
  contextBranch: document.getElementById("contextBranch"),
  contextPath: document.getElementById("contextPath"),
  contextMessage: document.getElementById("contextMessage"),
  refreshContextButton: document.getElementById("refreshContextButton"),
  branchCount: document.getElementById("branchCount"),
  archivedCount: document.getElementById("archivedCount"),
  projectCount: document.getElementById("projectCount"),
  listSummary: document.getElementById("listSummary"),
  branchList: document.getElementById("branchList"),
  projectPanel: document.getElementById("projectPanel"),
  projectBoard: document.getElementById("projectBoard"),
  closeProjectPanelButton: document.getElementById("closeProjectPanelButton"),
  archivePanel: document.getElementById("archivePanel"),
  archiveBoard: document.getElementById("archiveBoard"),
  closeArchivePanelButton: document.getElementById("closeArchivePanelButton"),
  timelineDrawer: document.getElementById("timelineDrawer"),
  closeDrawerButton: document.getElementById("closeDrawerButton"),
  drawerTitle: document.getElementById("drawerTitle"),
  drawerSubtitle: document.getElementById("drawerSubtitle"),
  drawerProject: document.getElementById("drawerProject"),
  drawerBranch: document.getElementById("drawerBranch"),
  drawerStatusButton: document.getElementById("drawerStatusButton"),
  drawerCount: document.getElementById("drawerCount"),
  drawerPath: document.getElementById("drawerPath"),
  drawerUpdated: document.getElementById("drawerUpdated"),
  appendChangeButton: document.getElementById("appendChangeButton"),
  archiveBranchButton: document.getElementById("archiveBranchButton"),
  appendComposer: document.getElementById("appendComposer"),
  appendHeading: document.getElementById("appendHeading"),
  appendForm: document.getElementById("appendForm"),
  appendSummaryInput: document.getElementById("appendSummaryInput"),
  appendLocalPathInput: document.getElementById("appendLocalPathInput"),
  appendDetailInput: document.getElementById("appendDetailInput"),
  appendCancelButton: document.getElementById("appendCancelButton"),
  timelineSummary: document.getElementById("timelineSummary"),
  timelineList: document.getElementById("timelineList"),
  overlayBackdrop: document.getElementById("overlayBackdrop"),
  toast: document.getElementById("toast"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

function showToast(message, isError = false) {
  els.toast.textContent = message;
  els.toast.classList.remove("hidden");
  els.toast.style.background = isError
    ? "color-mix(in oklch, oklch(0.52 0.18 30) 84%, white 16%)"
    : "color-mix(in oklch, oklch(0.28 0.03 45) 90%, white 10%)";
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    els.toast.classList.add("hidden");
  }, 2800);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}


function linesToArray(value) {
  return String(value ?? "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}


function arrayToLines(items) {
  return Array.isArray(items) ? items.join("\n") : "";
}

function statusClass(status) {
  return status === "已上线" ? "released" : "pending";
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function computeCounts(groups) {
  return {
    total: groups.length,
    projects: new Set(groups.map((group) => group.project)).size,
  };
}

function renderCounts(groups) {
  const counts = computeCounts(groups);
  els.branchCount.textContent = String(counts.total);
  els.archivedCount.textContent = String(state.archivedBranches.length);
  els.projectCount.textContent = String(counts.projects);
}

function renderContext(payload) {
  state.context = payload.git;
  if (payload.git.available && payload.git.context) {
    const { project, branch, repo_root: repoRoot } = payload.git.context;
    els.contextProject.textContent = project;
    els.contextBranch.textContent = branch;
    els.contextPath.textContent = repoRoot || "-";
    els.contextMessage.textContent = "当前工作区已绑定到本地 Web UI。";
    return;
  }

  els.contextProject.textContent = "-";
  els.contextBranch.textContent = "-";
  els.contextPath.textContent = "-";
  els.contextMessage.textContent = payload.git.error || "当前目录不是 Git 仓库";
}

function renderProjectFilterOptions(projects) {
  const previousValue = els.projectFilter.value;
  els.projectFilter.innerHTML = '<option value="">全部项目</option>';
  projects.forEach((project) => {
    const option = document.createElement("option");
    option.value = project.project;
    option.textContent = project.project;
    els.projectFilter.append(option);
  });
  if (previousValue && projects.some((project) => project.project === previousValue)) {
    els.projectFilter.value = previousValue;
  }
}

function renderProjectPanel(projects) {
  els.projectBoard.innerHTML = "";
  if (!projects.length) {
    els.projectBoard.className = "project-board empty";
    els.projectBoard.textContent = "暂无项目统计";
    return;
  }

  els.projectBoard.className = "project-board";
  projects.forEach((project) => {
    const row = document.createElement("article");
    row.className = `project-row ${project.project === els.projectFilter.value ? "active" : ""}`;
    row.innerHTML = `
      <div class="project-main">
        <strong>${escapeHtml(project.project)}</strong>
        <div class="project-meta">
          <span>${project.total} 个活跃分支</span>
        </div>
      </div>
      <div class="project-updated">${formatTime(project.latest_updated_at)}</div>
    `;
    row.addEventListener("click", () => {
      els.projectFilter.value = project.project;
      closeProjectPanel();
      applyFilters();
    });
    els.projectBoard.append(row);
  });
}

function renderArchivePanel(branches) {
  els.archiveBoard.innerHTML = "";
  if (!branches.length) {
    els.archiveBoard.className = "project-board empty";
    els.archiveBoard.textContent = "暂无归档分支";
    return;
  }

  els.archiveBoard.className = "project-board";
  branches.forEach((branch) => {
    const row = document.createElement("article");
    row.className = "archive-row";
    row.innerHTML = `
      <div class="archive-main">
        <strong>${escapeHtml(branch.branch)}</strong>
        <div class="project-meta">
          <span>${escapeHtml(branch.project)}</span>
          <span>${branch.entries_count} 条节点</span>
          <span>${formatTime(branch.archived_at || branch.latest_updated_at)}</span>
        </div>
      </div>
      <div class="archive-actions">
        <button type="button" class="secondary-button compact-button archive-restore-button">恢复</button>
        <button type="button" class="danger-button compact-button archive-delete-button">删除</button>
      </div>
    `;
    row.querySelector(".archive-restore-button").addEventListener("click", async () => {
      try {
        await setBranchArchive(branch, false);
      } catch (error) {
        showToast(error.message, true);
      }
    });
    row.querySelector(".archive-delete-button").addEventListener("click", async () => {
      try {
        await deleteBranchPermanently(branch);
      } catch (error) {
        showToast(error.message, true);
      }
    });
    els.archiveBoard.append(row);
  });
}

function findGroup(groupId) {
  return state.branches.find((group) => group.group_id === groupId) || null;
}

function findGroupByContext(project, branch) {
  return state.branches.find((group) => group.project === project && group.branch === branch) || null;
}

function findRecordInGroup(group, recordId) {
  if (!group) {
    return null;
  }
  return group.timeline.find((item) => item.id === recordId) || null;
}

function applyFilters() {
  const query = els.searchInput.value.trim().toLowerCase();
  const project = els.projectFilter.value;

  state.filteredBranches = state.branches.filter((group) => {
    if (project && group.project !== project) {
      return false;
    }
    if (!query) {
      return true;
    }

    const historyText = group.timeline
      .map((entry) => [entry.summary, entry.local_path, entry.detail_markdown].join("\n"))
      .join("\n");
    const haystack = [group.project, group.branch, group.release_status, historyText].join("\n").toLowerCase();
    return haystack.includes(query);
  });

  renderCounts(state.filteredBranches);
  renderBranchList();
  renderProjectPanel(state.projects);

  if (
    state.selectedGroupId &&
    !state.filteredBranches.some((group) => group.group_id === state.selectedGroupId)
  ) {
    closeDrawer(true);
  }
}

function renderBranchList() {
  els.listSummary.textContent = `${state.filteredBranches.length} 个分支`;
  els.branchList.innerHTML = "";

  if (!state.filteredBranches.length) {
    els.branchList.className = "branch-list empty";
    els.branchList.textContent = "没有符合当前筛选条件的分支";
    return;
  }

  els.branchList.className = "branch-list";

  state.filteredBranches.forEach((group) => {
    const row = document.createElement("article");
    row.className = `branch-item ${group.group_id === state.selectedGroupId ? "active" : ""}`;
    row.innerHTML = `
      <button type="button" class="branch-main-button">
        <div class="branch-topline">
          <span class="branch-project">${escapeHtml(group.project)}</span>
        </div>
        <strong class="branch-name">${escapeHtml(group.branch)}</strong>
        <div class="branch-bottomline">
          <span class="branch-updated">最近更新 ${formatTime(group.latest_updated_at)}</span>
        </div>
      </button>
      <div class="branch-actions">
        <button type="button" class="branch-status-button ${statusClass(group.release_status)}" aria-label="切换分支上线状态">${escapeHtml(group.release_status)}</button>
        <button type="button" class="branch-archive-button" aria-label="归档分支" ${group.release_status !== "已上线" ? "disabled" : ""}>归档</button>
        <button type="button" class="branch-delete-button" aria-label="删除分支">删除</button>
      </div>
    `;
    row.querySelector(".branch-main-button").addEventListener("click", () => openGroupDrawer(group.group_id));
    row.querySelector(".branch-status-button").addEventListener("click", async () => {
      try {
        await toggleBranchReleaseStatus(group);
      } catch (error) {
        showToast(error.message, true);
      }
    });
    row.querySelector(".branch-archive-button").addEventListener("click", async () => {
      try {
        await setBranchArchive(group, true);
      } catch (error) {
        showToast(error.message, true);
      }
    });
    row.querySelector(".branch-delete-button").addEventListener("click", async () => {
      try {
        await deleteBranchPermanently(group);
      } catch (error) {
        showToast(error.message, true);
      }
    });
    els.branchList.append(row);
  });
}

async function toggleBranchReleaseStatus(group) {
  const nextStatus = group.release_status === "已上线" ? "未上线" : "已上线";
  await api("/api/branches/release-status", {
    method: "PATCH",
    body: JSON.stringify({
      project: group.project,
      branch: group.branch,
      release_status: nextStatus,
    }),
  });
  await loadBranches();
  if (state.selectedGroupId === group.group_id) {
    renderDrawer();
  }
  showToast(`分支 ${group.branch} 已改为${nextStatus}`);
}

async function setBranchArchive(group, archived) {
  const confirmed = window.confirm(
    archived
      ? `确定归档分支 ${group.branch} 吗？\n归档后它将从首页分支列表中隐藏，但仍可在归档面板中恢复。`
      : `确定恢复分支 ${group.branch} 吗？\n恢复后它会重新出现在首页分支列表中。`
  );
  if (!confirmed) {
    return;
  }

  await api("/api/branches/archive", {
    method: "PATCH",
    body: JSON.stringify({
      project: group.project,
      branch: group.branch,
      archived,
    }),
  });

  if (archived && state.selectedGroupId === group.group_id) {
    closeDrawer(true);
  }

  await loadBranches();
  showToast(archived ? `已归档分支 ${group.branch}` : `已恢复分支 ${group.branch}`);
}

async function deleteBranchPermanently(group) {
  const confirmed = window.confirm(
    `确定永久删除分支 ${group.branch} 吗？\n该操作会删除此分支的全部时间轴节点，且不可恢复。`
  );
  if (!confirmed) {
    return;
  }

  await api("/api/branches", {
    method: "DELETE",
    body: JSON.stringify({
      project: group.project,
      branch: group.branch,
    }),
  });

  if (state.selectedGroupId === group.group_id) {
    closeDrawer(true);
  }

  await loadBranches();
  showToast(`已删除分支 ${group.branch}`);
}

function renderDrawer() {
  if (!state.drawerOpen) {
    return;
  }

  const group = state.selectedGroupId ? findGroup(state.selectedGroupId) : null;
  const context = state.drawerContext;
  const latest = group ? group.timeline[0] : null;

  els.drawerTitle.textContent = context?.branch || "未选择分支";
  els.drawerSubtitle.textContent = group
    ? "时间轴节点默认折叠，点击节点后可直接修改。"
    : "当前分支暂无历史节点，可以直接追加第一条变更。";
  els.drawerProject.textContent = context?.project || "-";
  els.drawerBranch.textContent = context?.branch || "-";
  els.drawerStatusButton.textContent = group?.release_status || "未上线";
  els.drawerStatusButton.className = `secondary-button compact-button drawer-status-button ${statusClass(group?.release_status || "未上线")}`;
  els.drawerCount.textContent = String(group ? group.entries_count : 0);
  els.drawerPath.textContent = latest?.local_path || context?.local_path || "-";
  els.drawerUpdated.textContent = latest ? formatTime(latest.updated_at) : "-";

  els.appendChangeButton.disabled = !context;
  els.archiveBranchButton.disabled = !group || group.release_status !== "已上线";
  renderAppendComposer(group, latest);
  renderTimeline(group);
}

function renderAppendComposer(group, latest) {
  els.appendComposer.classList.toggle("hidden", !state.appendMode);
  if (!state.appendMode) {
    return;
  }

  const context = state.drawerContext;
  els.appendHeading.textContent = context
    ? `追加 ${context.project} / ${context.branch} 的新节点`
    : "追加新的时间轴节点";
  els.appendSummaryInput.value = "";
  els.appendLocalPathInput.value = latest?.local_path || context?.local_path || "";
  els.appendDetailInput.value = latest?.detail_markdown || latest?.summary || "";
}

function renderTimeline(group) {
  els.timelineList.innerHTML = "";

  if (!group) {
    els.timelineSummary.textContent = "0 条";
    els.timelineList.className = "timeline-list empty";
    els.timelineList.textContent = "当前分支还没有时间轴节点";
    return;
  }

  els.timelineSummary.textContent = `${group.entries_count} 条`;
  els.timelineList.className = "timeline-list";

  group.timeline.forEach((entry) => {
    const isExpanded = state.selectedRecordId === entry.id;
    const node = document.createElement("article");
    node.className = "timeline-node";
    node.innerHTML = `
      <div class="timeline-node-header">
        <div>
          <div class="timeline-node-meta">
            <span>${formatTime(entry.created_at)}</span>
          </div>
          <p class="timeline-node-summary">${escapeHtml(entry.summary || "暂无内容")}</p>
          <p class="timeline-node-path">${escapeHtml(entry.local_path || "未记录本地地址")}</p>
        </div>
        <div class="timeline-node-actions">
          <button class="secondary-button compact-button" type="button" data-action="toggle">
            ${isExpanded ? "收起" : "展开"}
          </button>
        </div>
      </div>
      <div class="timeline-node-editor ${isExpanded ? "" : "hidden"}">
        <div class="node-grid">
          <label class="field">
            <span>总结</span>
            <input type="text" data-field="summary" value="${escapeHtml(entry.summary || "")}" />
          </label>
          <label class="field">
            <span>本地地址</span>
            <input type="text" data-field="local_path" value="${escapeHtml(entry.local_path || "")}" />
          </label>
        </div>
        <div class="detail-grid">
          <label class="field">
            <span>功能点</span>
            <textarea rows="3" data-field="feature_points">${escapeHtml(arrayToLines(entry.feature_points))}</textarea>
          </label>
          <label class="field">
            <span>修改文件</span>
            <textarea rows="3" data-field="modified_files">${escapeHtml(arrayToLines(entry.modified_files))}</textarea>
          </label>
          <label class="field detail-grid-full">
            <span>备注</span>
            <textarea rows="2" data-field="remarks">${escapeHtml(arrayToLines(entry.remarks))}</textarea>
          </label>
        </div>
        <label class="field">
          <span>详细记录内容</span>
          <textarea rows="8" data-field="detail_markdown">${escapeHtml(entry.detail_markdown || entry.summary || "")}</textarea>
        </label>
        <div class="timeline-node-actions">
          <button class="primary-button compact-button" type="button" data-action="save">保存修改</button>
          <button class="danger-button compact-button" type="button" data-action="delete">删除节点</button>
        </div>
      </div>
    `;

    node.querySelector('[data-action="toggle"]').addEventListener("click", () => {
      state.selectedRecordId = isExpanded ? "" : entry.id;
      renderDrawer();
    });

    node.querySelector('[data-action="save"]').addEventListener("click", async () => {
      try {
        await saveNodeEdit(entry.id, node);
      } catch (error) {
        showToast(error.message, true);
      }
    });

    node.querySelector('[data-action="delete"]').addEventListener("click", async () => {
      try {
        await deleteNode(entry.id);
      } catch (error) {
        showToast(error.message, true);
      }
    });

    els.timelineList.append(node);
  });
}

async function saveNodeEdit(recordId, node) {
  const payload = {
    summary: node.querySelector('[data-field="summary"]').value.trim(),
    local_path: node.querySelector('[data-field="local_path"]').value.trim(),
    feature_points: linesToArray(node.querySelector('[data-field="feature_points"]').value),
    modified_files: linesToArray(node.querySelector('[data-field="modified_files"]').value),
    remarks: linesToArray(node.querySelector('[data-field="remarks"]').value),
    detail_markdown: node.querySelector('[data-field="detail_markdown"]').value.trim(),
  };

  if (!payload.summary && !payload.detail_markdown) {
    showToast("总结和详细记录内容不能同时为空", true);
    return;
  }

  await api(`/api/records/${encodeURIComponent(recordId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

  await loadBranches();
  state.selectedRecordId = recordId;
  renderDrawer();
  showToast("时间轴节点已更新");
}

async function deleteNode(recordId) {
  if (!window.confirm("确定删除当前时间轴节点吗？")) {
    return;
  }

  await api(`/api/records/${encodeURIComponent(recordId)}`, { method: "DELETE" });
  await loadBranches();

  const group = state.selectedGroupId ? findGroup(state.selectedGroupId) : null;
  if (!group) {
    closeDrawer(true);
    return;
  }

  state.selectedRecordId = "";
  renderDrawer();
  showToast("时间轴节点已删除");
}

function openDrawer(drawerContext) {
  closeProjectPanel();
  closeArchivePanel();
  state.drawerOpen = true;
  state.drawerContext = drawerContext;
  els.timelineDrawer.classList.add("open");
  els.timelineDrawer.setAttribute("aria-hidden", "false");
  syncBackdrop();
  renderDrawer();
}

function closeDrawer(clearSelection = true) {
  state.drawerOpen = false;
  if (clearSelection) {
    state.selectedGroupId = "";
    state.selectedRecordId = "";
    state.drawerContext = null;
  }
  state.appendMode = false;
  els.timelineDrawer.classList.remove("open");
  els.timelineDrawer.setAttribute("aria-hidden", "true");
  syncBackdrop();
  renderBranchList();
}

function openGroupDrawer(groupId) {
  const group = findGroup(groupId);
  if (!group) {
    return;
  }

  state.selectedGroupId = group.group_id;
  state.selectedRecordId = "";
  state.appendMode = false;
  openDrawer({
    project: group.project,
    branch: group.branch,
    local_path: group.latest_local_path || "",
    group_id: group.group_id,
  });
  renderBranchList();
}

function openContextAppendDrawer() {
  const context = state.context?.context;
  if (!state.context?.available || !context) {
    showToast("当前工作区不可用，无法追加变更", true);
    return;
  }

  const group = findGroupByContext(context.project, context.branch);
  state.selectedGroupId = group?.group_id || "";
  state.selectedRecordId = "";
  state.appendMode = true;
  openDrawer({
    project: context.project,
    branch: context.branch,
    local_path: context.repo_root || "",
    group_id: group?.group_id || "",
  });
  renderBranchList();
}

function closeProjectPanel() {
  state.projectPanelOpen = false;
  els.projectPanel.classList.remove("open");
  els.projectPanel.setAttribute("aria-hidden", "true");
  syncBackdrop();
}

function openProjectPanel() {
  closeDrawer();
  closeArchivePanel();
  state.projectPanelOpen = true;
  els.projectPanel.classList.add("open");
  els.projectPanel.setAttribute("aria-hidden", "false");
  syncBackdrop();
}

function closeArchivePanel() {
  state.archivePanelOpen = false;
  els.archivePanel.classList.remove("open");
  els.archivePanel.setAttribute("aria-hidden", "true");
  syncBackdrop();
}

function openArchivePanel() {
  closeDrawer();
  closeProjectPanel();
  state.archivePanelOpen = true;
  els.archivePanel.classList.add("open");
  els.archivePanel.setAttribute("aria-hidden", "false");
  syncBackdrop();
}

function syncBackdrop() {
  const visible = state.projectPanelOpen || state.archivePanelOpen || state.drawerOpen;
  els.overlayBackdrop.classList.toggle("hidden", !visible);
}

async function loadContext() {
  const payload = await api("/api/context");
  renderContext(payload);
}

async function loadBranches() {
  const [activePayload, archivedPayload] = await Promise.all([
    api("/api/branches"),
    api("/api/archived-branches"),
  ]);
  state.branches = activePayload.branches;
  state.archivedBranches = archivedPayload.branches;
  state.projects = activePayload.projects;
  renderProjectFilterOptions(activePayload.projects);
  renderProjectPanel(activePayload.projects);
  renderArchivePanel(archivedPayload.branches);
  applyFilters();

  if (state.drawerOpen) {
    if (state.selectedGroupId && !findGroup(state.selectedGroupId)) {
      state.selectedGroupId = "";
      state.selectedRecordId = "";
    }
    renderDrawer();
  }
}

async function appendChange(event) {
  event.preventDefault();

  if (!state.drawerContext) {
    showToast("没有可追加的分支上下文", true);
    return;
  }

  const payload = {
    project: state.drawerContext.project,
    branch: state.drawerContext.branch,
    summary: els.appendSummaryInput.value.trim(),
    local_path: els.appendLocalPathInput.value.trim(),
    detail_markdown: els.appendDetailInput.value.trim(),
  };

  if (!payload.summary && !payload.detail_markdown) {
    showToast("总结和详细记录内容不能同时为空", true);
    return;
  }

  const response = await api("/api/records", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  await loadBranches();
  const group = findGroupByContext(payload.project, payload.branch);
  if (group) {
    state.selectedGroupId = group.group_id;
  }
  state.selectedRecordId = response.action === "created" ? response.record.id : "";
  state.appendMode = false;
  renderDrawer();

  if (response.action === "unchanged") {
    showToast("没有检测到变化，未新增时间轴节点");
  } else {
    showToast("已追加新的时间轴节点");
  }
}

function bindEvents() {
  [els.searchInput, els.projectFilter].forEach((element) => {
    element.addEventListener("input", applyFilters);
    element.addEventListener("change", applyFilters);
  });

  els.reloadButton.addEventListener("click", async () => {
    try {
      await loadBranches();
      showToast("分支列表已刷新");
    } catch (error) {
      showToast(error.message, true);
    }
  });

  els.refreshContextButton.addEventListener("click", async () => {
    try {
      await loadContext();
      showToast("工作区上下文已刷新");
    } catch (error) {
      showToast(error.message, true);
    }
  });

  els.projectPanelButton.addEventListener("click", openProjectPanel);
  els.closeProjectPanelButton.addEventListener("click", closeProjectPanel);
  els.archivePanelButton.addEventListener("click", openArchivePanel);
  els.closeArchivePanelButton.addEventListener("click", closeArchivePanel);

  els.currentChangeButton.addEventListener("click", openContextAppendDrawer);
  els.closeDrawerButton.addEventListener("click", () => closeDrawer());

  els.appendChangeButton.addEventListener("click", () => {
    if (!state.drawerContext) {
      return;
    }
    state.appendMode = true;
    renderDrawer();
  });

  els.drawerStatusButton.addEventListener("click", async () => {
    const group = state.selectedGroupId ? findGroup(state.selectedGroupId) : null;
    if (!group) {
      return;
    }
    try {
      await toggleBranchReleaseStatus(group);
    } catch (error) {
      showToast(error.message, true);
    }
  });

  els.archiveBranchButton.addEventListener("click", async () => {
    const group = state.selectedGroupId ? findGroup(state.selectedGroupId) : null;
    if (!group) {
      return;
    }
    try {
      await setBranchArchive(group, true);
    } catch (error) {
      showToast(error.message, true);
    }
  });

  els.appendCancelButton.addEventListener("click", () => {
    state.appendMode = false;
    renderDrawer();
  });

  els.appendForm.addEventListener("submit", async (event) => {
    try {
      await appendChange(event);
    } catch (error) {
      showToast(error.message, true);
    }
  });

  els.overlayBackdrop.addEventListener("click", () => {
    closeProjectPanel();
    closeArchivePanel();
    closeDrawer();
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeProjectPanel();
      closeArchivePanel();
      closeDrawer();
    }
  });
}

async function boot() {
  bindEvents();
  try {
    await Promise.all([loadContext(), loadBranches()]);
  } catch (error) {
    showToast(error.message, true);
  }
}

boot();
