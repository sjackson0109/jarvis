"""
Provider Configuration Panel – view and configure LLM providers.
Copyright 2026 sjackson0109
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox,
    QPushButton, QLineEdit, QTextEdit, QWidget, QScrollArea, QFormLayout,
    QCheckBox, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ProviderConfigDialog(QDialog):
    """
    Dialog for viewing and configuring LLM providers.

    Shows:
    - Registered providers with availability status
    - Hardware profile
    - Provider selection policy settings
    - Active provider/model selection
    """

    def __init__(self, parent=None, cfg=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("⚙️ Provider & Model Configuration")
        self.setMinimumSize(650, 550)
        self._cfg = cfg
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("⚙️ Provider & Model Configuration")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)

        # Hardware profile section
        hw_group = QGroupBox("🖥️ Hardware Profile")
        hw_layout = QFormLayout(hw_group)
        self._hw_labels = {
            "RAM": QLabel("–"),
            "CPU Cores": QLabel("–"),
            "Architecture": QLabel("–"),
            "Execution Mode": QLabel("–"),
            "Model Tier": QLabel("–"),
        }
        for key, lbl in self._hw_labels.items():
            hw_layout.addRow(f"{key}:", lbl)
        self._btn_refresh_hw = QPushButton("🔄 Refresh Hardware Profile")
        self._btn_refresh_hw.clicked.connect(self._refresh_hardware)
        hw_layout.addRow("", self._btn_refresh_hw)
        content_layout.addWidget(hw_group)

        # Registered providers section
        providers_group = QGroupBox("🌐 Registered Providers")
        providers_layout = QVBoxLayout(providers_group)
        self._providers_text = QTextEdit()
        self._providers_text.setReadOnly(True)
        self._providers_text.setMaximumHeight(120)
        providers_layout.addWidget(self._providers_text)
        self._btn_check_avail = QPushButton("🔍 Check Availability")
        self._btn_check_avail.clicked.connect(self._check_availability)
        providers_layout.addWidget(self._btn_check_avail)
        content_layout.addWidget(providers_group)

        # Provider policy section
        policy_group = QGroupBox("📋 Provider Selection Policy")
        policy_layout = QFormLayout(policy_group)

        self._privacy_combo = QComboBox()
        self._privacy_combo.addItems(["local_only", "prefer_local", "allow_public"])
        policy_layout.addRow("Privacy level:", self._privacy_combo)

        self._force_provider = QLineEdit()
        self._force_provider.setPlaceholderText("Leave empty for auto-selection")
        policy_layout.addRow("Force provider ID:", self._force_provider)

        self._force_model = QLineEdit()
        self._force_model.setPlaceholderText("Leave empty to use provider default")
        policy_layout.addRow("Force model ID:", self._force_model)

        content_layout.addWidget(policy_group)

        # Anthropic configuration
        anthropic_group = QGroupBox("🤖 Anthropic Claude (optional)")
        anthropic_layout = QFormLayout(anthropic_group)
        self._anthropic_key = QLineEdit()
        self._anthropic_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._anthropic_key.setPlaceholderText("sk-ant-api03-...")
        anthropic_layout.addRow("API Key:", self._anthropic_key)

        self._anthropic_model = QLineEdit()
        self._anthropic_model.setPlaceholderText("claude-3-5-haiku-20241022")
        anthropic_layout.addRow("Model:", self._anthropic_model)
        content_layout.addWidget(anthropic_group)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_save = QPushButton("💾 Save Policy Settings")
        self._btn_save.clicked.connect(self._save_policy)
        btn_row.addWidget(self._btn_save)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _refresh(self) -> None:
        self._refresh_hardware()
        self._refresh_providers()
        self._load_policy()

    def _refresh_hardware(self) -> None:
        try:
            from jarvis.hardware import get_hardware_profile
            profile = get_hardware_profile(force_refresh=True)
            self._hw_labels["RAM"].setText(f"{profile.total_ram_gb} GB total / {profile.available_ram_gb} GB free")
            self._hw_labels["CPU Cores"].setText(f"{profile.cpu_physical_cores} physical / {profile.cpu_logical_cores} logical")
            self._hw_labels["Architecture"].setText(f"{profile.cpu_architecture} ({profile.os_platform})")
            self._hw_labels["Execution Mode"].setText(profile.recommended_mode.value.replace("_", " ").title())
            self._hw_labels["Model Tier"].setText(profile.recommended_model_tier.title())
        except Exception as e:
            for lbl in self._hw_labels.values():
                lbl.setText(f"Error: {e}")

    def _refresh_providers(self) -> None:
        try:
            from jarvis.providers.registry import get_provider_registry
            registry = get_provider_registry()
            description = registry.describe_all()
            self._providers_text.setPlainText(description)
        except Exception as e:
            self._providers_text.setPlainText(f"Error loading providers: {e}")

    def _check_availability(self) -> None:
        try:
            from jarvis.providers.registry import get_provider_registry
            from jarvis.providers.base import ProviderStatus
            registry = get_provider_registry()
            lines = []
            for pid, p in registry.all_providers().items():
                status = p.check_availability()
                icon = "✅" if status == ProviderStatus.AVAILABLE else "❌"
                lines.append(f"{icon} [{pid}] {p.info.display_name}: {status.value}")
            self._providers_text.setPlainText("\n".join(lines) if lines else "No providers registered.")
        except Exception as e:
            self._providers_text.setPlainText(f"Error checking availability: {e}")

    def _load_policy(self) -> None:
        if self._cfg is None:
            return
        privacy = getattr(self._cfg, "provider_privacy_level", "prefer_local")
        idx = self._privacy_combo.findText(privacy)
        if idx >= 0:
            self._privacy_combo.setCurrentIndex(idx)
        self._force_provider.setText(getattr(self._cfg, "provider_force_id", "") or "")
        self._force_model.setText(getattr(self._cfg, "provider_force_model", "") or "")
        self._anthropic_model.setText(getattr(self._cfg, "anthropic_model", "claude-3-5-haiku-20241022") or "")
        # Never pre-fill the API key (security)

    def _save_policy(self) -> None:
        try:
            from pathlib import Path
            import json
            import os
            cfg_path_env = os.environ.get("JARVIS_CONFIG_PATH")
            from jarvis.config import _default_config_path
            cfg_path = Path(cfg_path_env).expanduser() if cfg_path_env else _default_config_path()
            existing = {}
            if cfg_path.exists():
                with cfg_path.open("r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing["provider_privacy_level"] = self._privacy_combo.currentText()
            force_id = self._force_provider.text().strip()
            existing["provider_force_id"] = force_id if force_id else None
            force_model = self._force_model.text().strip()
            existing["provider_force_model"] = force_model if force_model else None
            anthropic_key = self._anthropic_key.text().strip()
            if anthropic_key:
                existing["anthropic_api_key"] = anthropic_key
            anthropic_model = self._anthropic_model.text().strip()
            if anthropic_model:
                existing["anthropic_model"] = anthropic_model
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            with cfg_path.open("w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            QMessageBox.information(self, "Saved", "Provider policy saved. Restart Jarvis for changes to take effect.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save: {e}")
