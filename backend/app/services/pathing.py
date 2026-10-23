import heapq
from dataclasses import dataclass

from .matching import SkillRef

_RANK_REQUIRED, _RANK_PREFERRED = 0, 1


@dataclass(frozen=True)
class PathStep:
    step: int
    skill_id: str
    name: str
    category: str
    priority: str          # "required" | "preferred" | "prerequisite"
    reason: str
    depends_on: list[str]  # names of earlier steps this one builds on


def build_learning_path(
    targets: list[SkillRef],
    have_ids: set[str],
    prerequisites: dict,
    catalog: dict,
) -> list[PathStep]:
    """Order the skills to learn so prerequisites always come first.

    - targets: job skills the resume lacks (or only partly covers)
    - prerequisites that the resume already has are skipped
    - among skills that are ready to learn, required ones come before preferred ones, and a
      prerequisite inherits the priority of the most important skill that needs it
    """
    rank: dict[str, int] = {}
    needed_for: dict[str, set[str]] = {}
    target_by_id = {t.skill_id: t for t in targets}

    def add(skill_id: str, r: int) -> None:
        if skill_id in rank and rank[skill_id] <= r:
            return
        rank[skill_id] = r
        for pre in prerequisites.get(skill_id, ()):
            if pre in have_ids:
                continue
            needed_for.setdefault(pre, set()).add(skill_id)
            add(pre, r)

    for t in targets:
        add(t.skill_id, _RANK_REQUIRED if t.required else _RANK_PREFERRED)

    nodes = set(rank)
    deps = {n: [p for p in prerequisites.get(n, ()) if p in nodes] for n in nodes}
    dependents: dict[str, list[str]] = {n: [] for n in nodes}
    for n, pres in deps.items():
        for p in pres:
            dependents[p].append(n)
    indegree = {n: len(deps[n]) for n in nodes}

    def name(n: str) -> str:
        return catalog[n]["name"]

    heap = [(rank[n], name(n), n) for n in nodes if indegree[n] == 0]
    heapq.heapify(heap)
    steps: list[PathStep] = []
    while heap:
        _, _, n = heapq.heappop(heap)
        target = target_by_id.get(n)
        if target is not None:
            priority = "required" if target.required else "preferred"
            reason = "Required by this job" if target.required else "Nice to have for this job"
        else:
            priority = "prerequisite"
            reason = "Prerequisite for " + ", ".join(sorted(name(x) for x in needed_for.get(n, ())))
        steps.append(
            PathStep(
                step=len(steps) + 1,
                skill_id=n,
                name=name(n),
                category=catalog[n]["category"],
                priority=priority,
                reason=reason,
                depends_on=sorted(name(p) for p in deps[n]),
            )
        )
        for d in dependents[n]:
            indegree[d] -= 1
            if indegree[d] == 0:
                heapq.heappush(heap, (rank[d], name(d), d))
    return steps
