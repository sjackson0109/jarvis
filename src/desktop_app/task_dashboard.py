"""
Task Dashboard – operational visibility into tasks, pipelines, and agent state.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

from typing import List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QLabel, QPushButton, QWidget, QTextEdit,
    QGroupBox, QHeaderView, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor


class TaskDashboardDialog(QDialog):
    """
    Operational dashboard for task, pipeline, and agent visibility.

    Shows:
    - Active task state (Kanban-style columns)
    - Running sub-agents
    - Recent task history
    - Blocked decisions awaiting user input
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("📊 Task Dashboard")
        self.setMinimumSize(800, 600)
        self._setup_ui()
        self._setup_refresh_timer()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("📊 Operational Dashboard")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        tabs = QTabWidget()

        # Tab 1: Active Task
        active_tab = QWidget()
        active_layout = QVBoxLayout(active_tab)
        self._active_task_label = QLabel("No active task")
        self._active_task_label.setWordWrap(True)
        active_layout.addWidget(self._active_task_label)

        self._steps_table = QTableWidget(0, 4)
        self._steps_table.setHorizontalHeaderLabels(["Step", "Tool", "Status", "Duration"])
        self._steps_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._steps_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        active_layout.addWidget(self._steps_table)

        tabs.addTab(active_tab, "🔄 Active Task")

        # Tab 2: Kanban board (task status columns)
        kanban_tab = QWidget()
        kanban_layout = QHBoxLayout(kanban_tab)

        for col_name, col_icon in [
            ("Pending", "⏳"),
            ("Running", "🔄"),
            ("Awaiting Approval", "⚠️"),
            ("Done", "✅"),
            ("Failed", "❌"),
        ]:
            col_widget = QGroupBox(f"{col_icon} {col_name}")
            col_layout = QVBoxLayout(col_widget)
            list_widget = QListWidget()
            col_layout.addWidget(list_widget)
            setattr(self, f"_kanban_{col_name.lower().replace(' ', '_')}", list_widget)
            kanban_layout.addWidget(col_widget)

        tabs.addTab(kanban_tab, "📋 Kanban Board")

        # Tab 3: Sub-agents
        agents_tab = QWidget()
        agents_layout = QVBoxLayout(agents_tab)
        agents_layout.addWidget(QLabel("Active sub-agents:"))
        self._agents_table = QTableWidget(0, 4)
        self._agents_table.setHorizontalHeaderLabels(["Agent ID", "Template", "Task", "State"])
        self._agents_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        agents_layout.addWidget(self._agents_table)
        tabs.addTab(agents_tab, "🤖 Sub-Agents")

        # Tab 4: Recent task history
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.addWidget(QLabel("Recent completed tasks:"))
        self._history_table = QTableWidget(0, 4)
        self._history_table.setHorizontalHeaderLabels(["Task", "Project", "Status", "Started"])
        self._history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        history_layout.addWidget(self._history_table)
        self._btn_refresh_history = QPushButton("🔄 Refresh History")
        self._btn_refresh_history.clicked.connect(self._refresh_history)
        history_layout.addWidget(self._btn_refresh_history)
        tabs.addTab(history_tab, "📜 History")

        layout.addWidget(tabs)

        # Bottom: refresh button and close
        btn_row = QHBoxLayout()
        self._btn_refresh = QPushButton("🔄 Refresh")
        self._btn_refresh.clicked.connect(self._refresh)
        btn_row.addWidget(self._btn_refresh)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _setup_refresh_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(3000)  # Refresh every 3 seconds

    def _refresh(self) -> None:
        self._refresh_active_task()
        self._refresh_agents()

    def _refresh_active_task(self) -> None:
        try:
            from jarvis.task_state import get_active_task, TaskStatus, StepStatus
            task = get_active_task()
            if task.status == TaskStatus.IDLE:
                self._active_task_label.setText("💤 No active task")
                self._steps_table.setRowCount(0)
                return

            status_icons = {
                TaskStatus.PLANNING: "📝",
                TaskStatus.EXECUTING: "🔄",
                TaskStatus.AWAITING_APPROVAL: "⚠️",
                TaskStatus.DONE: "✅",
                TaskStatus.FAILED: "❌",
            }
            icon = status_icons.get(task.status, "❓")
            self._active_task_label.setText(
                f"{icon} {task.status.value.replace('_', ' ').title()}: {task.intent[:100]}"
            )

            # Populate steps table
            self._steps_table.setRowCount(len(task.steps))
            step_colors = {
                StepStatus.PENDING: QColor("#888888"),
                StepStatus.RUNNING: QColor("#2196F3"),
                StepStatus.SUCCEEDED: QColor("#4CAF50"),
                StepStatus.FAILED: QColor("#F44336"),
                StepStatus.SKIPPED: QColor("#FF9800"),
            }
            for row, step in enumerate(task.steps):
                self._steps_table.setItem(row, 0, QTableWidgetItem(step.description[:60]))
                self._steps_table.setItem(row, 1, QTableWidgetItem(step.tool_name or "–"))
                status_item = QTableWidgetItem(step.status.value)
                color = step_colors.get(step.status, QColor("#888888"))
                status_item.setForeground(color)
                self._steps_table.setItem(row, 2, status_item)
                duration = "–"
                if step.started_at and step.finished_at:
                    duration = f"{step.finished_at - step.started_at:.1f}s"
                elif step.started_at:
                    import time
                    duration = f"{time.time() - step.started_at:.1f}s…"
                self._steps_table.setItem(row, 3, QTableWidgetItem(duration))

            # Update Kanban lists
            step_by_status: dict[str, list[str]] = {
                "pending": [], "running": [], "awaiting_approval": [],
                "done": [], "failed": [],
            }
            for step in task.steps:
                status_key = step.status.value
                if status_key == "succeeded":
                    status_key = "done"
                if status_key in step_by_status:
                    step_by_status[status_key].append(step.description[:50])

            for status_key, steps in step_by_status.items():
                list_widget = getattr(self, f"_kanban_{status_key}", None)
                if list_widget:
                    list_widget.clear()
                    for desc in steps:
                        list_widget.addItem(QListWidgetItem(desc))

        except Exception as e:
            self._active_task_label.setText(f"Error: {e}")

    def _refresh_agents(self) -> None:
        try:
            active_agents = []
            try:
                from jarvis import _global_sub_agent_orchestrator
                active_agents = _global_sub_agent_orchestrator.list_active()
            except (ImportError, AttributeError):
                pass

            self._agents_table.setRowCount(len(active_agents))
            for row, ctx in enumerate(active_agents):
                self._agents_table.setItem(row, 0, QTableWidgetItem(ctx.agent_id[:12] + "…"))
                self._agents_table.setItem(row, 1, QTableWidgetItem(ctx.template_id))
                self._agents_table.setItem(row, 2, QTableWidgetItem(ctx.delegated_task[:60]))
                self._agents_table.setItem(row, 3, QTableWidgetItem(ctx.state.value))
        except Exception:
            pass

    def _refresh_history(self) -> None:
        try:
            from jarvis.memory.task_memory import TaskMemoryStore
            store = TaskMemoryStore()
            records = store.list_recent(limit=20)
            self._history_table.setRowCount(len(records))
            import time
            for row, record in enumerate(records):
                self._history_table.setItem(row, 0, QTableWidgetItem(record.requirement[:60]))
                self._history_table.setItem(row, 1, QTableWidgetItem(record.project_id or "–"))
                self._history_table.setItem(row, 2, QTableWidgetItem(record.status.value))
                started = time.strftime("%Y-%m-%d %H:%M", time.localtime(record.started_at))
                self._history_table.setItem(row, 3, QTableWidgetItem(started))
        except Exception:
            pass
