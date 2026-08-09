from pathlib import Path


MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "alembic"
    / "versions"
    / "a91f2c6d4e10_add_structured_job_roles.py"
)


def test_role_seed_uses_deterministic_ids_without_extra_tables() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    deterministic_ids = [
        "10000000-0000-4000-8000-000000000001",
        "10000000-0000-4000-8000-000000000002",
        "10000000-0000-4000-8000-000000000003",
        "10000000-0000-4000-8000-000000000004",
        "10000000-0000-4000-8000-000000000005",
        "10000000-0000-4000-8000-000000000006",
    ]
    assert all(role_id in source for role_id in deterministic_ids)
    assert "gen_random_uuid()" not in source
    assert "job_role_seed_ownership" not in source
    assert "ON CONFLICT DO NOTHING" in source
    assert "DO UPDATE SET" not in source
    assert "existing.id = seed.id OR existing.name = seed.name" in source


def test_role_downgrade_deletes_only_matching_owned_id_name_pairs() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert "DELETE FROM job_roles" in source
    assert "job_roles.id = owned.id" in source
    assert "job_roles.name = owned.name" in source
    assert "DROP CONSTRAINT IF EXISTS" in source
    assert "jsonb_typeof(requirements) = 'array'" in source
    assert "jsonb_array_length(requirements)" in source
