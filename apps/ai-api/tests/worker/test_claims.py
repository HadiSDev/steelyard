"""A run moves queued → running → succeeded | failed, and only once."""
from __future__ import annotations

from sqlmodel import Session

from ai_api.worker.claims import (
    INTERRUPTED,
    claim,
    claim_next,
    finish,
    recover_interrupted,
    start_system_run,
)
from web_api.db.models import PipelineRunKind, PipelineRunStatus
from worker_testkit import add_run, get_run


def test_the_oldest_queued_run_is_claimed(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    newer = add_run(worker_engine, tenant["company_id"], "categorize", minutes_ago=1)
    older = add_run(worker_engine, tenant["company_id"], "sync", minutes_ago=5)

    with Session(worker_engine) as s:
        run = claim_next(s)

    assert run is not None and run.id == older
    claimed = get_run(worker_engine, older)
    assert claimed.status == PipelineRunStatus.RUNNING
    assert claimed.started_at is not None
    assert get_run(worker_engine, newer).status == PipelineRunStatus.QUEUED


def test_nothing_queued_claims_nothing(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    add_run(worker_engine, tenant["company_id"], "sync", status=PipelineRunStatus.SUCCEEDED)

    with Session(worker_engine) as s:
        assert claim_next(s) is None


def test_two_claimers_racing_for_one_run_never_share_it(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    run_id = add_run(worker_engine, tenant["company_id"], "categorize")

    with Session(worker_engine) as first, Session(worker_engine) as second:
        won = claim(first, run_id)
        lost = claim(second, run_id)
        assert claim_next(second) is None

    assert won is not None and won.id == run_id
    assert lost is None


def test_a_claimer_that_loses_one_run_takes_the_next(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    taken = add_run(worker_engine, tenant["company_id"], "sync", minutes_ago=5)
    waiting = add_run(worker_engine, tenant["company_id"], "categorize", minutes_ago=1)

    with Session(worker_engine) as other:
        claim(other, taken)
    with Session(worker_engine) as s:
        run = claim_next(s)

    assert run is not None and run.id == waiting


def test_interrupted_runs_are_failed_and_others_left_alone(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    running = add_run(worker_engine, tenant["company_id"], "sync",
                      status=PipelineRunStatus.RUNNING)
    queued = add_run(worker_engine, tenant["company_id"], "categorize")
    done = add_run(worker_engine, tenant["company_id"], "categorize",
                   status=PipelineRunStatus.SUCCEEDED)

    with Session(worker_engine) as s:
        assert recover_interrupted(s) == 1

    failed = get_run(worker_engine, running)
    assert failed.status == PipelineRunStatus.FAILED
    assert failed.error == INTERRUPTED
    assert failed.finished_at is not None
    assert get_run(worker_engine, queued).status == PipelineRunStatus.QUEUED
    assert get_run(worker_engine, done).status == PipelineRunStatus.SUCCEEDED


def test_a_run_finishes_with_its_summary(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    run_id = add_run(worker_engine, tenant["company_id"], "categorize")

    with Session(worker_engine) as s:
        claim(s, run_id)
        assert finish(s, run_id, summary={"categorized": 3}) is True

    run = get_run(worker_engine, run_id)
    assert run.status == PipelineRunStatus.SUCCEEDED
    assert run.summary == {"categorized": 3}
    assert run.error is None
    assert run.finished_at is not None


def test_a_run_fails_with_its_error(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    run_id = add_run(worker_engine, tenant["company_id"], "sync")

    with Session(worker_engine) as s:
        claim(s, run_id)
        finish(s, run_id, error="ERP unreachable")

    run = get_run(worker_engine, run_id)
    assert run.status == PipelineRunStatus.FAILED
    assert run.error == "ERP unreachable"


def test_a_finished_run_never_changes_again(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    run_id = add_run(worker_engine, tenant["company_id"], "sync")

    with Session(worker_engine) as s:
        claim(s, run_id)
        finish(s, run_id, summary={"invoices": 1})
        assert finish(s, run_id, error="late failure") is False
        assert claim(s, run_id) is None

    run = get_run(worker_engine, run_id)
    assert run.status == PipelineRunStatus.SUCCEEDED
    assert run.error is None


def test_a_queued_run_cannot_be_finished_without_being_claimed(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    run_id = add_run(worker_engine, tenant["company_id"], "sync")

    with Session(worker_engine) as s:
        assert finish(s, run_id, summary={}) is False

    assert get_run(worker_engine, run_id).status == PipelineRunStatus.QUEUED


def test_a_system_run_starts_running(worker_engine, make_tenant):
    tenant = make_tenant("Acme")

    with Session(worker_engine) as s:
        run = start_system_run(s, tenant["company_id"], PipelineRunKind.READ_DOCUMENTS)
        run_id = run.id

    stored = get_run(worker_engine, run_id)
    assert stored.status == PipelineRunStatus.RUNNING
    assert stored.requested_by == "system"
    assert stored.kind == "read_documents"
    assert stored.started_at is not None
