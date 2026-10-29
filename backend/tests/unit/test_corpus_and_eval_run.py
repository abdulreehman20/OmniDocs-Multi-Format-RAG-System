from src.config import Settings
from src.db.models import User
from src.evals.runner import run_eval_dataset
from src.services.corpus import bump_user_corpus_version, get_user_corpus_version


def test_bump_user_corpus_version(session):
    session.add(User(id="user-a", email="a@example.com"))
    session.commit()
    assert get_user_corpus_version(session, "user-a") == 0
    bump_user_corpus_version(session, "user-a")
    session.commit()
    assert get_user_corpus_version(session, "user-a") == 1


def test_eval_runner_dry_run(session):
    settings = Settings(
        database_url="sqlite://",
        database_url_pooled="sqlite://",
        neon_auth_base_url="https://auth.example.neon.tech/neondb/auth",
        eval_max_samples=5,
    )
    run = run_eval_dataset(session, settings, max_samples=5, use_llm=False)
    assert run.status == "succeeded"
    assert run.sample_count == 5
    assert "citation_validity" in run.aggregate_metrics
    assert "abstention_quality" in run.aggregate_metrics
