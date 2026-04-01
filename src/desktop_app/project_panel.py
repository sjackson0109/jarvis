"""
Project Management Panel – graphical project creation and selection.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QTextEdit, QGroupBox, QMessageBox,
    QSplitter, QWidget, QComboBox, QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class ProjectManagementDialog(QDialog):
    """
    Dialog for creating, editing, and selecting projects.

    Shows a list of projects on the left and details/policy on the right.
    Allows creating new projects, editing policy, and setting voice default.
    """

    project_changed = pyqtSignal(str)  # Emitted when active project changes (project_id)

    def __init__(self, parent=None, projects_dir: Optional[str] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🗂️ Project Management")
        self.setMinimumSize(700, 500)
        self._projects_dir = projects_dir

        # Lazy import to avoid circular imports at module level
        from jarvis.project.manager import ProjectManager
        self._manager = ProjectManager(projects_dir=projects_dir)

        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("🗂️ Project Management")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel("Create and manage project contexts. Each project scopes its own policy, memory, and guardrails.")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Splitter: list on left, details on right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: project list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.addWidget(QLabel("Projects:"))
        self._project_list = QListWidget()
        self._project_list.currentItemChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._project_list)

        btn_row = QHBoxLayout()
        self._btn_new = QPushButton("➕ New")
        self._btn_new.clicked.connect(self._create_project)
        self._btn_delete = QPushButton("🗑️ Delete")
        self._btn_delete.clicked.connect(self._delete_project)
        self._btn_delete.setEnabled(False)
        btn_row.addWidget(self._btn_new)
        btn_row.addWidget(self._btn_delete)
        left_layout.addLayout(btn_row)
        splitter.addWidget(left_widget)

        # Right: project details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)

        details_group = QGroupBox("Project Details")
        details_layout = QVBoxLayout(details_group)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self._name_edit = QLineEdit()
        name_row.addWidget(self._name_edit)
        details_layout.addLayout(name_row)

        details_layout.addWidget(QLabel("Description:"))
        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(60)
        details_layout.addWidget(self._desc_edit)

        self._voice_default_check = QCheckBox("📢 Set as voice-default project")
        details_layout.addWidget(self._voice_default_check)

        right_layout.addWidget(details_group)

        policy_group = QGroupBox("Policy Overrides")
        policy_layout = QVBoxLayout(policy_group)

        privacy_row = QHBoxLayout()
        privacy_row.addWidget(QLabel("Privacy level:"))
        self._privacy_combo = QComboBox()
        self._privacy_combo.addItems(["(inherit global)", "local_only", "prefer_local", "allow_public"])
        privacy_row.addWidget(self._privacy_combo)
        policy_layout.addLayout(privacy_row)

        autonomy_row = QHBoxLayout()
        autonomy_row.addWidget(QLabel("Autonomy mode:"))
        self._autonomy_combo = QComboBox()
        self._autonomy_combo.addItems(["manual", "semi_autonomous", "highly_autonomous"])
        autonomy_row.addWidget(self._autonomy_combo)
        policy_layout.addLayout(autonomy_row)

        policy_layout.addWidget(QLabel("Project prompt (appended to global):"))
        self._project_prompt_edit = QTextEdit()
        self._project_prompt_edit.setMaximumHeight(80)
        self._project_prompt_edit.setPlaceholderText("Optional project-specific instructions for the LLM...")
        policy_layout.addWidget(self._project_prompt_edit)

        right_layout.addWidget(policy_group)

        # Save/Activate buttons
        btn_row2 = QHBoxLayout()
        self._btn_save = QPushButton("💾 Save Changes")
        self._btn_save.clicked.connect(self._save_project)
        self._btn_save.setEnabled(False)
        self._btn_activate = QPushButton("✅ Set as Active Project")
        self._btn_activate.clicked.connect(self._activate_project)
        self._btn_activate.setEnabled(False)
        btn_row2.addWidget(self._btn_save)
        btn_row2.addWidget(self._btn_activate)
        right_layout.addLayout(btn_row2)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([250, 450])
        layout.addWidget(splitter)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _refresh_list(self) -> None:
        self._project_list.clear()
        for project in self._manager.list_all():
            label = project.name
            if project.is_voice_default:
                label += " 📢"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, project.id)
            self._project_list.addItem(item)

    def _on_selection_changed(self, current, previous) -> None:
        has_selection = current is not None
        self._btn_delete.setEnabled(has_selection)
        self._btn_save.setEnabled(has_selection)
        self._btn_activate.setEnabled(has_selection)
        if current:
            project_id = current.data(Qt.ItemDataRole.UserRole)
            project = self._manager.get(project_id)
            if project:
                self._name_edit.setText(project.name)
                self._desc_edit.setPlainText(project.description)
                self._voice_default_check.setChecked(project.is_voice_default)
                privacy = project.policy.provider_privacy_level or "(inherit global)"
                idx = self._privacy_combo.findText(privacy)
                self._privacy_combo.setCurrentIndex(max(0, idx))
                self._autonomy_combo.setCurrentText(project.policy.autonomy_mode.value)
                self._project_prompt_edit.setPlainText(project.policy.project_prompt)

    def _create_project(self) -> None:
        project = self._manager.create(name="New Project", description="")
        self._refresh_list()
        for i in range(self._project_list.count()):
            if self._project_list.item(i).data(Qt.ItemDataRole.UserRole) == project.id:
                self._project_list.setCurrentRow(i)
                break

    def _save_project(self) -> None:
        item = self._project_list.currentItem()
        if not item:
            return
        project_id = item.data(Qt.ItemDataRole.UserRole)
        project = self._manager.get(project_id)
        if not project:
            return

        from jarvis.project.model import AutonomyMode
        project.name = self._name_edit.text().strip() or "Unnamed Project"
        project.description = self._desc_edit.toPlainText().strip()

        privacy_text = self._privacy_combo.currentText()
        project.policy.provider_privacy_level = None if privacy_text == "(inherit global)" else privacy_text
        project.policy.autonomy_mode = AutonomyMode(self._autonomy_combo.currentText())
        project.policy.project_prompt = self._project_prompt_edit.toPlainText().strip()

        if self._voice_default_check.isChecked():
            self._manager.set_voice_default(project_id)
        self._manager.update(project)
        self._refresh_list()
        QMessageBox.information(self, "Saved", f"Project '{project.name}' saved.")

    def _delete_project(self) -> None:
        item = self._project_list.currentItem()
        if not item:
            return
        project_id = item.data(Qt.ItemDataRole.UserRole)
        project = self._manager.get(project_id)
        if not project:
            return
        reply = QMessageBox.question(
            self, "Delete Project",
            f"Delete project '{project.name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._manager.delete(project_id)
            self._refresh_list()

    def _activate_project(self) -> None:
        item = self._project_list.currentItem()
        if not item:
            return
        project_id = item.data(Qt.ItemDataRole.UserRole)
        project = self._manager.get(project_id)
        if not project:
            return
        from jarvis.project.context import set_active_project
        set_active_project(project)
        self.project_changed.emit(project_id)
        QMessageBox.information(self, "Activated", f"✅ Active project set to: {project.name}")
