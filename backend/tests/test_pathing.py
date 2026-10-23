import pytest

from app.services.matching import SkillRef
from app.services.pathing import build_learning_path
from app.services.relations import load_prerequisites, load_relations
from app.services.skills import load_vocabulary

CATALOG = load_vocabulary().skills
PREREQ = load_prerequisites()


def T(skill_id, required=True):
    return SkillRef(skill_id, CATALOG[skill_id]["name"], CATALOG[skill_id]["category"], required)


def order(steps):
    return [s.skill_id for s in steps]


def test_data_files_are_valid():
    assert len(load_relations()) > 30
    assert len(PREREQ) > 20


def test_prerequisite_comes_first_and_is_explained():
    steps = build_learning_path([T("postgresql")], set(), PREREQ, CATALOG)
    assert order(steps) == ["sql", "postgresql"]
    assert steps[0].priority == "prerequisite" and steps[0].reason == "Prerequisite for PostgreSQL"
    assert steps[1].depends_on == ["SQL"] and steps[1].priority == "required"


def test_prerequisite_already_owned_is_skipped():
    steps = build_learning_path([T("postgresql")], {"sql"}, PREREQ, CATALOG)
    assert order(steps) == ["postgresql"]


def test_required_before_preferred_when_independent():
    steps = build_learning_path([T("aws", required=False), T("docker")], set(), PREREQ, CATALOG)
    assert order(steps) == ["docker", "aws"]


def test_prerequisite_inherits_priority_of_what_needs_it():
    targets = [T("postgresql"), T("aws", required=False)]
    assert order(build_learning_path(targets, set(), PREREQ, CATALOG)) == ["sql", "postgresql", "aws"]


def test_chain_is_ordered_and_shared_prerequisites_appear_once():
    steps = build_learning_path([T("tensorflow"), T("pytorch")], set(), PREREQ, CATALOG)
    ids = order(steps)
    assert len(ids) == len(set(ids))
    assert ids.index("python") < ids.index("machine-learning") < ids.index("deep-learning")
    assert ids.index("deep-learning") < ids.index("tensorflow")
    assert ids.index("deep-learning") < ids.index("pytorch")


def test_nothing_to_learn_gives_empty_path():
    assert build_learning_path([], {"python"}, PREREQ, CATALOG) == []
