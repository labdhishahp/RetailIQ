"""Agent primitives shared by the specialists."""

from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from app.agents.tools import call_tool


@dataclass
class Finding:
    """One evidenced observation produced by a specialist."""

    statement: str
    severity: str = "info"        # info | warning | critical
    metric: float | None = None
    entity: str | None = None

    def as_dict(self) -> dict:
        return {"statement": self.statement, "severity": self.severity,
                "metric": self.metric, "entity": self.entity}


@dataclass
class AgentResult:
    agent: str
    task: str
    findings: list[Finding] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    duration_ms: int = 0

    @property
    def severity(self) -> str:
        if any(f.severity == "critical" for f in self.findings):
            return "critical"
        if any(f.severity == "warning" for f in self.findings):
            return "warning"
        return "info"

    def as_dict(self) -> dict:
        return {
            "agent": self.agent, "task": self.task, "severity": self.severity,
            "findings": [f.as_dict() for f in self.findings],
            "tools_called": self.tools_called, "data": self.data,
            "duration_ms": self.duration_ms,
        }


class Agent:
    """A specialist with a fixed scope, a toolset, and evidence-based output."""

    name: str = "agent"
    label: str = "Agent"
    task: str = ""
    icon: str = "Sparkles"

    def run(self, db: Session, context: dict) -> AgentResult:  # pragma: no cover
        raise NotImplementedError

    # helper so subclasses record which tools they used
    def _call(self, db: Session, result: AgentResult, tool: str, **kwargs):
        result.tools_called.append(tool)
        return call_tool(db, tool, **kwargs)


AgentFactory = Callable[[], Agent]
