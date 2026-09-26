"""System admins request pipeline runs for a company and list them."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from web_api.db.models import PipelineRun

from web_api_testkit import auth


def _request(client, company_id: str, kind: str, *, token: str = "tok_sysadmin"):
    return client.post(
        f"/api/v1/companies/{company_id}/runs", json={"kind": kind}, headers=auth(token)
    )


def _runs(engine, company_id: str) -> list[PipelineRun]:
    with Session(engine) as s:
        return list(s.exec(select(PipelineRun).where(PipelineRun.company_id == company_id)).all())


def test_a_system_admin_queues_a_sync(client, voucher_seed, engine):
    res = _request(client, voucher_seed["comp_a"], "sync")

    assert res.status_code == 201
    body = res.json()
    assert body["kind"] == "sync"
    assert body["status"] == "queued"
    assert body["started_at"] is None and body["finished_at"] is None
    assert len(_runs(engine, voucher_seed["comp_a"])) == 1


def test_the_run_names_the_admin_who_asked(client, seed, engine):
    res = _request(client, seed["comp_a"], "categorize")

    run = _runs(engine, seed["comp_a"])[0]
    assert res.json()["requested_by"] == run.requested_by
    assert run.requested_by not in ("", "system")


def test_an_org_admin_cannot_request_a_run(client, seed, engine):
    res = _request(client, seed["comp_a"], "categorize", token="tokA")

    assert res.status_code == 403
    assert _runs(engine, seed["comp_a"]) == []


def test_an_unknown_company_is_404(client, seed):
    assert _request(client, "no-such-company", "categorize").status_code == 404


def test_an_unknown_kind_is_422(client, seed, engine):
    assert _request(client, seed["comp_a"], "defragment").status_code == 422
    assert _runs(engine, seed["comp_a"]) == []


def test_a_sync_needs_a_connected_erp(client, seed, engine):
    res = _request(client, seed["comp_b"], "sync")

    assert res.status_code == 409
    assert _runs(engine, seed["comp_b"]) == []


def test_a_second_request_returns_the_run_already_waiting(client, seed, engine):
    first = _request(client, seed["comp_a"], "read_documents")
    second = _request(client, seed["comp_a"], "read_documents")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(_runs(engine, seed["comp_a"])) == 1


def test_a_different_kind_is_queued_beside_it(client, seed, engine):
    _request(client, seed["comp_a"], "read_documents")

    assert _request(client, seed["comp_a"], "categorize").status_code == 201
    assert len(_runs(engine, seed["comp_a"])) == 2


def test_a_finished_run_does_not_block_a_new_one(client, seed, engine):
    with Session(engine) as s:
        s.add(PipelineRun(company_id=seed["comp_a"], kind="categorize",
                          status="succeeded", requested_by="userSys"))
        s.commit()

    assert _request(client, seed["comp_a"], "categorize").status_code == 201


def _seed_runs(engine, company_id: str, count: int) -> None:
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    with Session(engine) as s:
        for index in range(count):
            s.add(PipelineRun(
                company_id=company_id, kind="categorize", status="succeeded",
                requested_by="userSys", requested_at=start + timedelta(minutes=index),
            ))
        s.commit()


def test_runs_are_listed_newest_first(client, seed, engine):
    _seed_runs(engine, seed["comp_a"], 3)

    res = client.get(f"/api/v1/companies/{seed['comp_a']}/runs", headers=auth("tok_sysadmin"))

    assert res.status_code == 200
    times = [run["requested_at"] for run in res.json()]
    assert times == sorted(times, reverse=True)


def test_the_list_defaults_to_twenty(client, seed, engine):
    _seed_runs(engine, seed["comp_a"], 25)

    res = client.get(f"/api/v1/companies/{seed['comp_a']}/runs", headers=auth("tok_sysadmin"))

    assert len(res.json()) == 20


def test_the_list_limit_is_capped_at_one_hundred(client, seed):
    res = client.get(
        f"/api/v1/companies/{seed['comp_a']}/runs?limit=101", headers=auth("tok_sysadmin")
    )

    assert res.status_code == 422


def test_only_a_system_admin_may_list_runs(client, seed):
    res = client.get(f"/api/v1/companies/{seed['comp_a']}/runs", headers=auth("tokA"))

    assert res.status_code == 403


def test_the_list_is_the_companys_own(client, seed, engine):
    _seed_runs(engine, seed["comp_b"], 2)

    res = client.get(f"/api/v1/companies/{seed['comp_a']}/runs", headers=auth("tok_sysadmin"))

    assert res.json() == []
