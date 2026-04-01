"""
Sub-agent template library.
Copyright 2026 sjackson0109

Defines specialist agent templates. Each template specifies the agent's
purpose, behavioural policy, prompt layers, memory policy, and guardrails.
Sub-agents are ephemeral by default – spawned for a task and then shut down.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentTemplate:
    """
    Template for an ephemeral specialist sub-agent.

    Each template defines everything needed to instantiate and run a
    focused specialist. Templates can be cloned and customised per project.
    """
    template_id: str
    name: str
    purpose: str
    # System prompt specific to this agent type
    agent_prompt: str = ""
    # Allowed tool classes for this agent (empty = inherit from project/global)
    allowed_tools: List[str] = field(default_factory=list)
    # Approval posture: how aggressively this agent seeks approval
    approval_posture: str = "standard"  # "strict", "standard", "permissive"
    # Whether the agent stores its own memory records
    store_memory: bool = True
    # Reporting style guidance (appended to prompt)
    reporting_style: str = ""
    # Fallback behaviour when stuck
    fallback_behaviour: str = "ask_user"   # "ask_user", "retry", "abandon"
    # Whether this is a built-in template (protected from deletion)
    is_builtin: bool = False
    # Arbitrary metadata for UI and extensibility
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "purpose": self.purpose,
            "agent_prompt": self.agent_prompt,
            "allowed_tools": self.allowed_tools,
            "approval_posture": self.approval_posture,
            "store_memory": self.store_memory,
            "reporting_style": self.reporting_style,
            "fallback_behaviour": self.fallback_behaviour,
            "is_builtin": self.is_builtin,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            purpose=data["purpose"],
            agent_prompt=data.get("agent_prompt", ""),
            allowed_tools=data.get("allowed_tools", []),
            approval_posture=data.get("approval_posture", "standard"),
            store_memory=data.get("store_memory", True),
            reporting_style=data.get("reporting_style", ""),
            fallback_behaviour=data.get("fallback_behaviour", "ask_user"),
            is_builtin=data.get("is_builtin", False),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Built-in specialist templates
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATES: List[AgentTemplate] = [
    AgentTemplate(
        template_id="solutions_architect",
        name="Solutions Architect",
        purpose="Design system architectures, evaluate trade-offs, and produce architecture decision records.",
        agent_prompt=(
            "You are a senior solutions architect. Focus on high-level design, scalability, "
            "maintainability, and cost. Produce clear architecture decision records (ADRs) "
            "with options considered, recommendation, and rationale. Avoid implementation detail "
            "unless specifically asked."
        ),
        allowed_tools=["webSearch", "fetchWebPage", "localFiles"],
        approval_posture="standard",
        reporting_style="ADR format with problem, options, decision, and consequences sections.",
        fallback_behaviour="ask_user",
        is_builtin=True,
    ),
    AgentTemplate(
        template_id="security_architect",
        name="Security Architect",
        purpose="Assess security posture, identify vulnerabilities, and recommend controls.",
        agent_prompt=(
            "You are a security architect. Analyse designs and implementations for security "
            "weaknesses. Reference OWASP, CIS, and relevant standards. Prioritise findings "
            "by severity. Provide actionable remediation steps."
        ),
        allowed_tools=["webSearch", "fetchWebPage", "localFiles"],
        approval_posture="strict",
        reporting_style="Findings report: severity, description, evidence, remediation.",
        fallback_behaviour="ask_user",
        is_builtin=True,
    ),
    AgentTemplate(
        template_id="django_developer",
        name="Django Web Developer",
        purpose="Implement Django web application features, models, views, and APIs.",
        agent_prompt=(
            "You are an experienced Django developer. Write clean, idiomatic Python and Django "
            "code following PEP 8 and Django best practices. Prefer class-based views, "
            "use the ORM effectively, and write tests for all new code."
        ),
        allowed_tools=["localFiles", "webSearch"],
        approval_posture="standard",
        reporting_style="Code with inline comments explaining design decisions.",
        fallback_behaviour="retry",
        is_builtin=True,
    ),
    AgentTemplate(
        template_id="infra_engineer",
        name="Infrastructure Engineer",
        purpose="Design and implement infrastructure as code, CI/CD pipelines, and deployment automation.",
        agent_prompt=(
            "You are a senior infrastructure engineer. Work with Terraform, Ansible, Docker, "
            "Kubernetes, and cloud providers. Produce idempotent, version-controlled infrastructure "
            "definitions. Document all choices."
        ),
        allowed_tools=["localFiles", "webSearch", "fetchWebPage"],
        approval_posture="strict",
        reporting_style="Infrastructure plan with resource list, dependencies, and rollback steps.",
        fallback_behaviour="ask_user",
        is_builtin=True,
    ),
    AgentTemplate(
        template_id="documentation_agent",
        name="Documentation Agent",
        purpose="Write, update, and improve technical documentation.",
        agent_prompt=(
            "You are a technical writer. Write clear, concise, and accurate documentation. "
            "Use British English. Structure content for the target audience. "
            "Prefer Markdown. Include examples and diagrams where helpful."
        ),
        allowed_tools=["localFiles", "webSearch"],
        approval_posture="permissive",
        reporting_style="Structured Markdown with headings, examples, and summary.",
        fallback_behaviour="ask_user",
        is_builtin=True,
    ),
    AgentTemplate(
        template_id="troubleshooting_agent",
        name="Troubleshooting Agent",
        purpose="Diagnose technical issues and guide resolution.",
        agent_prompt=(
            "You are a technical troubleshooter. Systematically diagnose issues using "
            "evidence-based reasoning. State your hypothesis, the evidence supporting it, "
            "and the next diagnostic step. Avoid guessing without evidence."
        ),
        allowed_tools=["webSearch", "fetchWebPage", "localFiles", "screenshot"],
        approval_posture="standard",
        reporting_style="Hypothesis → Evidence → Next step format.",
        fallback_behaviour="ask_user",
        is_builtin=True,
    ),
    AgentTemplate(
        template_id="research_agent",
        name="Research Agent",
        purpose="Gather, synthesise, and summarise information from multiple sources.",
        agent_prompt=(
            "You are a research specialist. Gather information from multiple sources, "
            "evaluate credibility, and synthesise findings into a clear, structured summary. "
            "Always cite your sources."
        ),
        allowed_tools=["webSearch", "fetchWebPage"],
        approval_posture="permissive",
        reporting_style="Structured summary with source citations.",
        fallback_behaviour="retry",
        is_builtin=True,
    ),
]
