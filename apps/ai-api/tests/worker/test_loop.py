"""One pass of the worker: a queued run, else pending documents, else nothing."""
from __future__ import annotations

import pytest
from sqlmodel import Session, select

from ai_api import config
from ai_api.documents import runner as documents_runner
from ai_api.worker import loop
from ai_api.worker.__main__ import main
from ai_api.worker.claims import INTERRUPTED
from ai_api.worker.loop import TickOutcome, run_worker, tick
from web_api.db.models import DocStatus, Invoice, InvoiceLine, LineStatus, PipelineRunStatus
from worker_testkit import add_run, all_runs, assign_default_tree, get_run


class _Stop(Exception):
    """Raised by the test sleep to end the otherwise endless loop."""


def _stop_on_sleep(seconds: float) -> None:
    raise _Stop()


def _doc_statuses(engine) -> dict[str, str]:
    with Session(engine) as s:
        return {invoice.company_id: invoice.doc_status for invoice in s.exec(select(Invoice)).all()}


def test_a_queued_categorize_run_is_executed(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    add_run(worker_engine, tenant["company_id"], "sync")
    assert tick(5) == TickOutcome.RAN
    assign_default_tree(worker_engine, tenant["company_id"])
    run_id = add_run(worker_engine, tenant["company_id"], "categorize")

    assert tick(5) == TickOutcome.RAN

    run = get_run(worker_engine, run_id)
    assert run.status == PipelineRunStatus.SUCCEEDED
    assert run.summary["categorized"] == 1
    assert run.started_at is not None and run.finished_at is not None
    with Session(worker_engine) as s:
        assert s.exec(select(InvoiceLine)).one().status == LineStatus.AI_CATEGORIZED


def test_a_failing_run_is_failed_and_the_next_still_runs(
    worker_engine, make_tenant, fake_connector
):
    tenant = make_tenant("Acme")
    fake_connector.reachable = False
    failing = add_run(worker_engine, tenant["company_id"], "sync", minutes_ago=5)
    following = add_run(worker_engine, tenant["company_id"], "categorize", minutes_ago=1)

    assert tick(5) == TickOutcome.RAN
    assert tick(5) == TickOutcome.RAN

    failed = get_run(worker_engine, failing)
    assert failed.status == PipelineRunStatus.FAILED
    assert "Could not reach" in failed.error
    assert get_run(worker_engine, following).status == PipelineRunStatus.SUCCEEDED


def test_the_loop_keeps_going_past_a_failing_run(worker_engine, make_tenant, fake_connector):
    tenant = make_tenant("Acme")
    fake_connector.reachable = False
    failing = add_run(worker_engine, tenant["company_id"], "sync", minutes_ago=5)
    following = add_run(worker_engine, tenant["company_id"], "categorize", minutes_ago=1)

    with pytest.raises(_Stop):
        run_worker(poll_seconds=5, document_batch=5, sleep=_stop_on_sleep)

    assert get_run(worker_engine, failing).status == PipelineRunStatus.FAILED
    assert get_run(worker_engine, following).status == PipelineRunStatus.SUCCEEDED


def test_pending_documents_are_read_as_a_system_run(
    worker_engine, documented_tenant, offline_reads
):
    tenant = documented_tenant("Acme")

    assert tick(5) == TickOutcome.READ

    runs = all_runs(worker_engine)
    assert len(runs) == 1
    run = runs[0]
    assert run.company_id == tenant["company_id"]
    assert run.kind == "read_documents"
    assert run.requested_by == "system"
    assert run.status == PipelineRunStatus.SUCCEEDED
    assert run.summary["processed"] == 1
    assert _doc_statuses(worker_engine) == {tenant["company_id"]: DocStatus.PROCESSED}


def test_each_company_with_pending_documents_gets_its_own_run(
    worker_engine, documented_tenant, offline_reads
):
    acme = documented_tenant("Acme")
    globex = documented_tenant("Globex")

    assert tick(5) == TickOutcome.READ

    runs = all_runs(worker_engine)
    assert sorted(run.company_id for run in runs) == sorted(
        [acme["company_id"], globex["company_id"]]
    )
    assert all(run.summary["processed"] == 1 for run in runs)


def test_a_batch_reads_no_more_than_its_size(worker_engine, documented_tenant, offline_reads):
    documented_tenant("Acme")
    documented_tenant("Globex")

    assert tick(1) == TickOutcome.READ

    assert len(all_runs(worker_engine)) == 1
    statuses = sorted(_doc_statuses(worker_engine).values())
    assert statuses == sorted([DocStatus.PROCESSED, DocStatus.PENDING])


def test_a_queued_run_goes_before_pending_documents(
    worker_engine, documented_tenant, offline_reads
):
    tenant = documented_tenant("Acme")
    run_id = add_run(worker_engine, tenant["company_id"], "categorize")

    assert tick(5) == TickOutcome.RAN

    assert get_run(worker_engine, run_id).status == PipelineRunStatus.SUCCEEDED
    assert _doc_statuses(worker_engine) == {tenant["company_id"]: DocStatus.PENDING}


def test_a_crashing_automatic_read_is_recorded_as_failed(
    worker_engine, documented_tenant, monkeypatch
):
    documented_tenant("Acme")

    def crash(**kwargs):
        raise RuntimeError("vision model gone")

    monkeypatch.setattr(documents_runner, "run_documents", crash)

    assert tick(5) == TickOutcome.READ

    run = all_runs(worker_engine)[0]
    assert run.status == PipelineRunStatus.FAILED
    assert run.error == "vision model gone"


def test_an_idle_tick_records_nothing(worker_engine, make_tenant):
    make_tenant("Acme")

    assert tick(5) == TickOutcome.IDLE

    assert all_runs(worker_engine) == []


def test_the_loop_sleeps_only_when_idle(worker_engine, make_tenant):
    make_tenant("Acme")
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        raise _Stop()

    with pytest.raises(_Stop):
        run_worker(poll_seconds=7, document_batch=5, sleep=sleep)

    assert slept == [7]


def test_a_tick_that_crashes_does_not_stop_the_loop(worker_engine, monkeypatch):
    def broken(document_batch: int) -> TickOutcome:
        raise ConnectionError("database restarting")

    monkeypatch.setattr(loop, "tick", broken)

    with pytest.raises(_Stop):
        run_worker(poll_seconds=5, document_batch=5, sleep=_stop_on_sleep)


def test_starting_the_worker_fails_interrupted_runs(worker_engine, make_tenant):
    tenant = make_tenant("Acme")
    stuck = add_run(worker_engine, tenant["company_id"], "sync",
                    status=PipelineRunStatus.RUNNING)

    assert run_worker(poll_seconds=5, document_batch=5, once=True) == TickOutcome.IDLE

    run = get_run(worker_engine, stuck)
    assert run.status == PipelineRunStatus.FAILED
    assert run.error == INTERRUPTED


def test_the_entry_point_runs_one_pass(worker_engine, make_tenant, monkeypatch, capsys):
    tenant = make_tenant("Acme")
    run_id = add_run(worker_engine, tenant["company_id"], "categorize")
    monkeypatch.setattr(config, "WORKER_DOCUMENT_BATCH", 1)

    assert main(["--once"]) == 0

    assert get_run(worker_engine, run_id).status == PipelineRunStatus.SUCCEEDED
    assert "ran" in capsys.readouterr().out


def test_the_worker_settings_have_defaults():
    assert config.WORKER_POLL_SECONDS > 0
    assert config.WORKER_DOCUMENT_BATCH > 0
