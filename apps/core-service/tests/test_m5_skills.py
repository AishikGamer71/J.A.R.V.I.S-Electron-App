from pathlib import Path

from jarvis.domain.entities.models import ChatMessage, MessageRole
from jarvis.gateway.server import add_skill_context
from jarvis.skills.catalog import SkillCatalog
from jarvis.skills.catalog import skill_catalog


def write_skill(root: Path, name: str, description: str, instructions: str, extra: str = "") -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\ntags: [testing]\n{extra}---\n{instructions}\n",
        encoding="utf-8",
    )


def test_catalog_loads_valid_skill_and_selects_relevant_context(tmp_path: Path):
    write_skill(
        tmp_path,
        "research-brief",
        "Research and summarize reliable public sources.",
        "Cite direct sources and clearly distinguish facts from inferences.",
        "agents: [chat_agent]\n",
    )
    write_skill(
        tmp_path,
        "file-notes",
        "Organize local notes safely.",
        "Use the sandboxed file tools only after approval.",
    )

    catalog = SkillCatalog(roots=[tmp_path])
    result = catalog.reload()

    assert result["loaded"] == 2
    assert [skill.manifest.name for skill in catalog.list_skills()] == ["file-notes", "research-brief"]

    context = catalog.build_prompt_context("Please research current battery technology", agent_name="chat_agent")
    assert "research-brief" in context
    assert "Cite direct sources" in context
    assert "file-notes" not in context


def test_catalog_rejects_invalid_skill_without_breaking_other_skills(tmp_path: Path):
    write_skill(
        tmp_path,
        "valid-skill",
        "A valid skill for test coverage.",
        "Follow the local rules.",
    )
    invalid_dir = tmp_path / "invalid"
    invalid_dir.mkdir()
    (invalid_dir / "SKILL.md").write_text("# Missing front matter\n", encoding="utf-8")

    catalog = SkillCatalog(roots=[tmp_path])
    result = catalog.reload()

    assert result["loaded"] == 1
    assert catalog.get("valid-skill") is not None
    assert len(result["errors"]) == 1
    assert "must begin with YAML front matter" in result["errors"][0]


def test_gateway_prompt_context_uses_only_matching_local_skills(tmp_path: Path):
    write_skill(
        tmp_path,
        "release-notes",
        "Create accurate software release notes.",
        "Summarize changes by user impact and call out migrations.",
        "agents: [chat_agent]\n",
    )
    original_roots = skill_catalog.roots
    try:
        skill_catalog.roots = [tmp_path]
        skill_catalog.reload()
        messages = [
            ChatMessage(
                session_id="skill-test",
                role=MessageRole.USER,
                content="Draft release notes for this update",
            )
        ]

        enriched = add_skill_context(messages)

        assert len(enriched) == 2
        assert enriched[0].role == MessageRole.SYSTEM
        assert "release-notes" in enriched[0].content
        assert enriched[-1] == messages[0]
    finally:
        skill_catalog.roots = original_roots
        skill_catalog.reload()
