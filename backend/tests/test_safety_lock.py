"""Server-side Module D coaching lock: open safety events block every coaching
endpoint with HTTP 423 until a clinician acknowledges them."""
import ast
from datetime import timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

from database import Base, get_db
from main import app
from models.admin_user import AdminSession, AdminUser, hash_password
from models.care_plan import CarePlan
from models.checkin import CheckInSession
from models.safety_event import SafetyEvent, SAFETY_STATUS_ACKNOWLEDGED, SAFETY_STATUS_OPEN
from models.temporary_audio import TemporaryAudio
from models.user import User
from services.safety_engine import EMERGENCY_SCRIPT
from services.safety_lock import require_no_open_safety_event
from utils import ist_now

CHECKIN_BODY = {
    "q1_activity_days": 3, "q2_food_goal_days": 3, "q3_medication_days": 7, "q4_foot_care_days": 7,
    "q5_new_foot_problem": False, "q6_stress_0_10": 3, "q7_sleep_0_10": 7, "q8_sugar_reading": 140,
}


@pytest.fixture
async def session_maker(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    yield maker
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def client(session_maker):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def patient(session_maker):
    """A patient with one of everything a coaching endpoint can serve."""
    async with session_maker() as db:
        user = User(display_user_id="ravikuma45", first_name="Ravi", last_name="Kumar", preferred_language="en")
        db.add(user)
        await db.flush()
        plan = CarePlan(user_id=user.id, risk_tier="amber", plan_snapshot={"clinical_status": {"note": "x"}}, traceability={})
        db.add(plan)
        await db.flush()
        audio = TemporaryAudio(user_id=user.id, care_plan_id=plan.id, content_hash="h", language="en-IN",
                               provider="sarvam", file_path="missing.wav", expires_at=ist_now() + timedelta(hours=1))
        checkin = CheckInSession(user_id=user.id, program_week=1, due_date=ist_now().date(), status="due")
        db.add_all([audio, checkin])
        await db.commit()
        return {"user_id": user.id, "care_plan_id": plan.id, "asset_id": audio.id, "checkin_id": checkin.id}


@pytest.fixture
async def admin_token(session_maker):
    async with session_maker() as db:
        admin = AdminUser(username="clinician", password_hash=hash_password("pw-12345678"), display_name="Dr Clinician")
        db.add(admin)
        await db.flush()
        session = AdminSession.create(admin.id)
        db.add(session)
        await db.commit()
        return session.token


async def open_event(session_maker, user_id, code="chest_pain"):
    async with session_maker() as db:
        event = SafetyEvent(user_id=user_id, source_module="1", trigger_code=code)
        db.add(event)
        await db.commit()
        return event.id


async def get_event(session_maker, event_id):
    async with session_maker() as db:
        return (await db.execute(select(SafetyEvent).where(SafetyEvent.id == event_id))).scalar()


def coaching_requests(p):
    return [
        ("POST", f"/api/care-plan/generate?user_id={p['user_id']}", None),
        ("GET", f"/api/care-plan/{p['care_plan_id']}", None),
        ("GET", f"/api/care-plan/user/{p['user_id']}/latest", None),
        ("POST", f"/api/care-plan/{p['care_plan_id']}/tts", {"language": "en-IN"}),
        ("GET", f"/api/temporary-audio/{p['asset_id']}", None),
        ("GET", f"/api/checkin/user/{p['user_id']}/sessions", None),
        ("POST", f"/api/checkin/sessions/{p['checkin_id']}/complete", CHECKIN_BODY),
        ("GET", f"/api/adherence/user/{p['user_id']}/current", None),
        ("GET", f"/api/adherence/user/{p['user_id']}/history", None),
    ]


def api_routes():
    """Flatten app.routes; newer FastAPI wraps each included router."""
    routes = []
    for r in app.routes:
        original = getattr(r, "original_router", None)
        routes.extend(original.routes if original is not None else [r])
    return [r for r in routes if getattr(r, "path", "").startswith("/api/")]


async def call(client, method, url, body):
    return await client.request(method, url, json=body)


def assert_locked(resp, code, language="en"):
    assert resp.status_code == 423, (resp.request.url, resp.status_code, resp.text)
    detail = resp.json()["detail"]
    assert detail["error"] == "safety_lock"
    assert detail["locked"] is True
    assert detail["event_code"] == code
    assert detail["language"] == language
    assert detail["emergency_script"] == EMERGENCY_SCRIPT[language]


async def test_locked_patient_gets_423_on_every_coaching_endpoint(client, session_maker, patient):
    await open_event(session_maker, patient["user_id"], "chest_pain")
    for method, url, body in coaching_requests(patient):
        assert_locked(await call(client, method, url, body), "chest_pain")


async def test_lock_script_is_in_patients_language(client, session_maker, patient):
    await open_event(session_maker, patient["user_id"], "self_harm")
    assert (await client.patch(f"/api/users/{patient['user_id']}/language", json={"preferred_language": "ta"})).status_code == 200
    for method, url, body in coaching_requests(patient):
        assert_locked(await call(client, method, url, body), "self_harm", language="ta")


async def test_unlocked_patient_is_unaffected(client, session_maker, patient):
    for method, url, body in coaching_requests(patient):
        resp = await call(client, method, url, body)
        assert resp.status_code != 423, (url, resp.text)
    assert (await client.get(f"/api/care-plan/{patient['care_plan_id']}")).status_code == 200
    assert (await client.get(f"/api/care-plan/user/{patient['user_id']}/latest")).status_code == 200


async def test_another_patients_open_event_does_not_lock_this_patient(client, session_maker, patient):
    async with session_maker() as db:
        other = User(display_user_id="other", first_name="O", last_name="P")
        db.add(other)
        await db.commit()
    await open_event(session_maker, other.id)
    assert (await client.get(f"/api/care-plan/user/{patient['user_id']}/latest")).status_code == 200


async def test_open_endpoints_still_work_while_locked(client, session_maker, patient):
    uid = patient["user_id"]
    await open_event(session_maker, uid)

    assert (await client.patch(f"/api/users/{uid}/language", json={"preferred_language": "en"})).status_code == 200
    assert (await client.get("/api/conversation/script")).status_code == 200

    script = await client.get("/api/safety/emergency-script", params={"language": "ta"})
    assert script.status_code == 200 and script.json()["emergency_script"] == EMERGENCY_SCRIPT["ta"]

    status = (await client.get(f"/api/safety/user/{uid}/status")).json()
    assert status["locked"] is True and status["emergency_script"] == EMERGENCY_SCRIPT["en"]


async def test_answer_submission_and_screening_continue_while_locked(client, session_maker, patient):
    uid = patient["user_id"]
    await open_event(session_maker, uid, "chest_pain")

    sess = await client.post(f"/api/conversation/sessions?user_id={uid}",
                             json={"script_id": "s", "script_version": "1", "sitting": "3"})
    assert sess.status_code == 201
    sid = sess.json()["id"]

    consent = await client.post(f"/api/conversation/sessions/{sid}/responses", json={
        "module_id": "A", "question_id": "consent", "answer_value": "yes", "language": "en"})
    assert consent.status_code == 200
    resp = await client.post(f"/api/conversation/sessions/{sid}/responses", json={
        "module_id": "M3", "question_id": "missed_dose_reason", "answer_value": "I want to end my life", "language": "en"})
    assert resp.status_code == 200

    done = await client.post(f"/api/conversation/sessions/{sid}/complete-sitting", json={"sitting": "3"})
    assert done.status_code == 200 and done.json()["status"] == "completed"

    # Module D still screened the new answer and opened a second event.
    async with session_maker() as db:
        codes = {e.trigger_code for e in (await db.execute(
            select(SafetyEvent).where(SafetyEvent.user_id == uid, SafetyEvent.status == SAFETY_STATUS_OPEN))).scalars()}
    assert codes == {"chest_pain", "self_harm"}


async def test_checkin_answers_are_saved_while_locked_but_coaching_withheld(client, session_maker, patient):
    await open_event(session_maker, patient["user_id"])
    resp = await client.post(f"/api/checkin/sessions/{patient['checkin_id']}/complete",
                             json={**CHECKIN_BODY, "q8_sugar_reading": 450})
    assert resp.status_code == 423
    async with session_maker() as db:
        saved = (await db.execute(select(CheckInSession).where(CheckInSession.id == patient["checkin_id"]))).scalar()
        new_events = (await db.execute(select(SafetyEvent).where(SafetyEvent.trigger_code == "sugar_above_400"))).scalars().all()
    assert saved.q8_sugar_reading == 450 and saved.status == "escalated"
    assert len(new_events) == 1


async def test_checkin_red_flag_locks_immediately(client, session_maker, patient):
    resp = await client.post(f"/api/checkin/sessions/{patient['checkin_id']}/complete",
                             json={**CHECKIN_BODY, "q8_sugar_reading": 55})
    assert_locked(resp, "sugar_below_70")
    assert (await client.get(f"/api/care-plan/user/{patient['user_id']}/latest")).status_code == 423


async def test_acknowledgement_unlocks(client, session_maker, patient, admin_token):
    event_id = await open_event(session_maker, patient["user_id"])
    auth = {"Authorization": f"Bearer {admin_token}"}

    queue = await client.get("/api/admin/safety-events", headers=auth)
    assert [e["id"] for e in queue.json()] == [event_id]

    ack = await client.post(f"/api/admin/safety-events/{event_id}/acknowledge",
                            json={"note": "Phoned patient; seen at PHC, ECG normal."}, headers=auth)
    assert ack.status_code == 200
    assert ack.json()["patientStillLocked"] is False

    event = await get_event(session_maker, event_id)
    assert event.status == SAFETY_STATUS_ACKNOWLEDGED and event.resolved is True
    assert event.acknowledged_at is not None and event.acknowledged_by is not None
    assert event.acknowledgement_note == "Phoned patient; seen at PHC, ECG normal."

    for method, url, body in coaching_requests(patient):
        assert (await call(client, method, url, body)).status_code != 423, url
    assert (await client.get(f"/api/safety/user/{patient['user_id']}/status")).json()["locked"] is False

    again = await client.post(f"/api/admin/safety-events/{event_id}/acknowledge", json={"note": "dup"}, headers=auth)
    assert again.status_code == 409


async def test_every_open_event_must_be_acknowledged(client, session_maker, patient, admin_token):
    first = await open_event(session_maker, patient["user_id"], "chest_pain")
    await open_event(session_maker, patient["user_id"], "fainting")
    ack = await client.post(f"/api/admin/safety-events/{first}/acknowledge", json={"note": "seen"},
                            headers={"Authorization": f"Bearer {admin_token}"})
    assert ack.json()["patientStillLocked"] is True
    assert_locked(await client.get(f"/api/care-plan/user/{patient['user_id']}/latest"), "fainting")


async def test_acknowledgement_requires_a_note(client, session_maker, patient, admin_token):
    event_id = await open_event(session_maker, patient["user_id"])
    resp = await client.post(f"/api/admin/safety-events/{event_id}/acknowledge", json={"note": "   "},
                             headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 422
    assert (await get_event(session_maker, event_id)).status == SAFETY_STATUS_OPEN


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer not-a-real-token"},
    "patient-id",
])
async def test_patient_cannot_acknowledge(client, session_maker, patient, headers):
    # Patients have no session token; the closest they can send is their own id.
    if headers == "patient-id":
        headers = {"Authorization": f"Bearer {patient['user_id']}"}
    event_id = await open_event(session_maker, patient["user_id"])
    resp = await client.post(f"/api/admin/safety-events/{event_id}/acknowledge", json={"note": "I feel fine"}, headers=headers)
    assert resp.status_code == 401
    assert (await get_event(session_maker, event_id)).status == SAFETY_STATUS_OPEN
    assert (await client.get(f"/api/care-plan/user/{patient['user_id']}/latest")).status_code == 423


def test_no_patient_route_can_change_event_status():
    patient_safety_routes = [r for r in api_routes() if "safety" in r.path and not r.path.startswith("/api/admin/")]
    assert patient_safety_routes
    for route in patient_safety_routes:
        assert route.methods <= {"GET", "HEAD"}, route.path
    acknowledge = [r for r in api_routes() if r.path.endswith("/acknowledge")]
    assert [r.path for r in acknowledge] == ["/api/admin/safety-events/{event_id}/acknowledge"]


async def test_acknowledged_answers_do_not_relock_on_next_sitting(client, session_maker, patient, admin_token):
    uid = patient["user_id"]

    async def sitting(n, answer):
        sid = (await client.post(f"/api/conversation/sessions?user_id={uid}",
                                 json={"script_id": "s", "script_version": "1", "sitting": n})).json()["id"]
        await client.post(f"/api/conversation/sessions/{sid}/responses", json={
            "module_id": "M3", "question_id": f"medications_{n}", "answer_value": answer, "language": "en"})
        assert (await client.post(f"/api/conversation/sessions/{sid}/complete-sitting", json={"sitting": n})).status_code == 200

    await sitting("1", "metformin, sometimes chest pain")
    status = (await client.get(f"/api/safety/user/{uid}/status")).json()
    assert status["locked"] and status["event_code"] == "chest_pain"

    await client.post(f"/api/admin/safety-events/{status['event_id']}/acknowledge", json={"note": "reviewed"},
                      headers={"Authorization": f"Bearer {admin_token}"})

    await sitting("2", "metformin only")
    assert (await client.get(f"/api/safety/user/{uid}/status")).json()["locked"] is False

    await sitting("3", "chest pain again today")
    assert (await client.get(f"/api/safety/user/{uid}/status")).json()["event_code"] == "chest_pain"


def test_coaching_routers_are_guarded():
    """Any route added under these prefixes later is locked by default."""
    guarded_prefixes = ("/api/care-plan", "/api/temporary-audio", "/api/adherence")
    guarded = [r for r in api_routes() if r.path.startswith(guarded_prefixes) or r.path == "/api/checkin/user/{user_id}/sessions"]
    assert len(guarded) == 8
    for route in guarded:
        calls = {d.call for d in route.dependant.dependencies}
        assert require_no_open_safety_event in calls, route.path


def test_speech_proxy_has_no_path_into_engine_or_lock():
    tree = ast.parse((Path(__file__).resolve().parent.parent / "routers" / "speech.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(m.startswith(("services", "routers", "models")) for m in imported), imported
