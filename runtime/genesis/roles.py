"""Role charters live in org/roles/<name>.md with a small frontmatter header.

The company rewrites these itself (via the define_role tool), which is how the
organization designs and evolves its own agents.
"""
import re
from dataclasses import dataclass, field

from .config import ROLES_DIR

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
MODELS = {"opus", "sonnet", "haiku", "fable"}
KINDS = {"leader", "worker"}


@dataclass
class Role:
    name: str
    title: str
    kind: str  # leader: one persistent instance; worker: spawned per task
    model: str
    reports_to: str
    heartbeat_minutes: int
    description: str
    charter: str
    version: int = 1
    meta: dict = field(default_factory=dict)


def parse(text: str, name: str) -> Role:
    meta, body = {}, text
    if text.startswith("---"):
        _, head, body = text.split("---", 2)
        for line in head.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return Role(
        name=name,
        title=meta.get("title", name),
        kind=meta.get("kind", "worker"),
        model=meta.get("model", "sonnet"),
        reports_to=meta.get("reports_to", "ceo"),
        heartbeat_minutes=int(meta.get("heartbeat_minutes", "0") or 0),
        description=meta.get("description", ""),
        charter=body.strip(),
        version=int(meta.get("version", "1") or 1),
        meta=meta,
    )


def render(r: Role) -> str:
    return (
        f"---\ntitle: {r.title}\nkind: {r.kind}\nmodel: {r.model}\nreports_to: {r.reports_to}\n"
        f"heartbeat_minutes: {r.heartbeat_minutes}\nversion: {r.version}\n"
        f"description: {r.description}\n---\n\n{r.charter.strip()}\n"
    )


def load_all() -> dict[str, Role]:
    out = {}
    for p in sorted(ROLES_DIR.glob("*.md")):
        try:
            out[p.stem] = parse(p.read_text(), p.stem)
        except Exception:
            continue
    return out


def load(name: str) -> Role | None:
    p = ROLES_DIR / f"{name}.md"
    return parse(p.read_text(), name) if p.exists() else None


def save(r: Role):
    ROLES_DIR.mkdir(parents=True, exist_ok=True)
    (ROLES_DIR / f"{r.name}.md").write_text(render(r))
