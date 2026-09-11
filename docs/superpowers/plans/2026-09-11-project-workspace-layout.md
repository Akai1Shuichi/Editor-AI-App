# Project Workspace Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the opened-project header and image-step controls while preserving the existing four-step workflow and all media-processing behavior.

**Architecture:** `ProjectWorkspace` remains the owner of project context and pipeline navigation, but its resource badges are collapsed into tab labels and its secondary actions move into one menu. `WatermarkTab` remains shared by project and standalone modes, with project-specific visibility applied from `set_project()` and a compact list toolbar shared by both modes.

**Tech Stack:** Python 3, PyQt6 widgets/layouts, `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-11-project-workspace-layout-design.md`

## Global Constraints

- Keep the four project steps and the standalone sidebar tools.
- Do not change project storage, worker, media-processing, or navigation behavior.
- Use blue only for selection/primary action and green only for successful status.
- Do not run tests, builds, linters, app launches, screenshots, or manual checks unless the user explicitly asks.
- Preserve the user's existing uncommitted changes in `app/ui/tts_tab.py`, `app/ui/watermark_tab.py`, and `tests/test_standalone_tools_ui.py`.

---

### Task 1: Simplify the project header and pipeline status

**Files:**
- Modify: `app/ui/project_workspace.py:1-420`
- Modify: `app/styles.py:640-790`
- Test: `tests/test_standalone_tools_ui.py`

**Interfaces:**
- Consumes: `Project.get_pipeline_summary() -> Dict[str, Any]`, `save_project_manually(silent: bool = False)`, `_on_auto_save_toggled(checked: bool)`.
- Produces: `action_auto_save: QAction`, compact `lbl_updated` text, and the existing `inner_tabs` with all status represented in tab text.

- [ ] **Step 1: Add a regression test for visible workspace state**

Create a temporary `Project`, call `workspace.set_project(project)`, and assert the header metadata is one compact line and pipeline counts appear in tab labels:

```python
self.assertEqual(
    workspace.lbl_updated.text(),
    "16:9 · 30 FPS · Đã lưu 11/09/2026 lúc 21:17",
)
self.assertEqual(workspace.inner_tabs.tabText(0), "1  Ảnh (9) ✓")
workspace.action_auto_save.setChecked(True)
self.assertTrue(workspace.tts_tab.auto_save)
```

This catches regressions where removed header badges return, metadata is scattered again, or the menu toggle stops controlling auto-save.

- [ ] **Step 2: Do not run the test under repository policy**

The relevant command for the user is:

```bash
python -m unittest tests.test_standalone_tools_ui.StandaloneToolsUiTests
```

- [ ] **Step 3: Replace the crowded header with two compact clusters**

Remove the four badge labels, the separate ratio/FPS chips, breadcrumb separator, and visible auto-save checkbox. Keep a title stack on the left and actions on the right:

```python
self.btn_back = QPushButton("←  Dự án")
self.lbl_project_name = QLabel("Chưa mở dự án")
self.lbl_updated = QLabel("")
self.btn_save = QPushButton("Lưu")

self.action_auto_save = QAction("Tự động lưu", self, checkable=True)
self.action_auto_save.toggled.connect(self._on_auto_save_toggled)
menu.addAction(self.action_auto_save)
menu.addSeparator()
menu.addAction(open_folder_action)
menu.addAction(rename_action)
menu.addSeparator()
menu.addAction(delete_action)
```

Set `workspace_header` maximum height to 64. Format its metadata in `set_project()` and after manual save:

```python
def _project_meta_text(self) -> str:
    if not self.current_project:
        return ""
    return (
        f"{self.current_project.aspect_ratio} · {self.current_project.fps} FPS · "
        f"Đã lưu {self._format_updated_at(self.current_project.updated_at)}"
    )
```

- [ ] **Step 4: Keep pipeline state only in tab labels**

Retain `refresh_pipeline_badges()` as the public/internal compatibility entry point, but remove all badge widget mutations. Use these exact formats:

```python
image_text = f"1  Ảnh ({clean_c}) ✓" if clean_c else (
    f"1  Ảnh ({raw_c})" if raw_c else "1  Ảnh"
)
voice_text = "2  Giọng nói ✓" if summary["voice_ready"] else (
    "2  Giọng nói ⚠" if summary["has_voice"] else "2  Giọng nói"
)
scene_text = (
    f"3  Kịch bản ({summary['scenes_count']}) ✓"
    if summary["has_scenes"] else "3  Kịch bản cảnh"
)
video_text = f"4  Xuất video ({vid_c}) ✓" if vid_c else "4  Xuất video"
```

Update `_clear_current_project()` to reset only these four labels.

- [ ] **Step 5: Tighten workspace styles**

Remove the earlier duplicate `#project_inner_tabs` block. Keep one definition with a 48 px tab bar, transparent tabs, one blue selected underline, and no pane border. Style `#workspace_header` and `#meta_label` for the compact two-level hierarchy.

- [ ] **Step 6: Commit Task 1 changes**

```bash
git add app/ui/project_workspace.py app/styles.py tests/test_standalone_tools_ui.py
git commit -m "refactor: simplify project workspace header"
```

### Task 2: Reorganize the image-step controls

**Files:**
- Modify: `app/ui/watermark_tab.py:1-680`
- Test: `tests/test_standalone_tools_ui.py`

**Interfaces:**
- Consumes: `on_files_selected(paths: List[Path])`, `clear_file_list()`, `delete_selected_row()`, `set_project(project)`.
- Produces: `lbl_file_count: QLabel`, `action_clear: QAction`, and `_update_file_count() -> None`.

- [ ] **Step 1: Add regression assertions for the image-step behavior**

Extend the existing watermark tests to assert the count label, accurate result-column title, and project-mode duplicate control visibility:

```python
self.assertEqual(tab.lbl_file_count.text(), "2 ảnh")
self.assertEqual(tab.table.horizontalHeaderItem(2).text(), "Kết quả")
tab.set_project(project)
self.assertTrue(tab.btn_select_files.isHidden())
```

After deleting a selected row, assert `lbl_file_count.text() == "1 ảnh"`. This catches missed state synchronization while avoiding assertions about pixel geometry.

- [ ] **Step 2: Do not run the test under repository policy**

The relevant command for the user is:

```bash
python -m unittest tests.test_standalone_tools_ui.StandaloneToolsUiTests
```

- [ ] **Step 3: Split input and list actions by responsibility**

Keep the drop area first. Place file-source actions on a small row immediately below it, then place list actions in a header directly above the table:

```python
source_row.addStretch()
source_row.addWidget(self.btn_select_files)
source_row.addWidget(self.btn_select_folder)

list_row.addWidget(QLabel("Danh sách ảnh"))
list_row.addWidget(self.lbl_file_count)
list_row.addStretch()
list_row.addWidget(self.btn_delete_selected)
list_row.addWidget(self.btn_list_menu)
```

Move `Xóa hết` into `btn_list_menu` as `action_clear`. In `set_project(project)`, hide `btn_select_files` when a project is active because the drop area already opens the file picker; leave it visible in standalone mode.

- [ ] **Step 4: Synchronize count and table semantics**

Rename the third header from `Thời Gian` to `Kết quả`. Add:

```python
def _update_file_count(self) -> None:
    count = len(self.selected_files)
    self.lbl_file_count.setText(f"{count} ảnh")
```

Call it after project hydration, file addition, selected-row deletion, and full clearing. Disable `action_clear` together with other list-editing controls while processing.

- [ ] **Step 5: Commit Task 2 changes**

```bash
git add app/ui/watermark_tab.py tests/test_standalone_tools_ui.py
git commit -m "refactor: organize project image controls"
```

### Task 3: Static review and handoff

**Files:**
- Review: `app/ui/project_workspace.py`
- Review: `app/ui/watermark_tab.py`
- Review: `app/styles.py`
- Review: `tests/test_standalone_tools_ui.py`

**Interfaces:**
- Consumes: completed Tasks 1 and 2.
- Produces: a clean patch with no whitespace errors and an explicit untested-status handoff.

- [ ] **Step 1: Check patch hygiene**

```bash
git diff --check
git status --short
```

- [ ] **Step 2: Review scope manually from the diff**

Confirm the diff does not change media workers, storage paths, signal payloads, or sidebar navigation. Confirm prior Voice TTS and watermark edits remain intact.

- [ ] **Step 3: Report verification limits**

State that `git diff --check` was run and that automated tests/build/app launch were not run under `.agents/AGENTS.md`.
