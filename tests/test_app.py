import copy
import urllib.parse
import importlib
import pytest
from fastapi.testclient import TestClient

import src.app as app_module
from src.app import app, activities

# keep a pristine copy of activities so each test can start fresh
ORIGINAL_ACTIVITIES = copy.deepcopy(activities)


@pytest.fixture(autouse=True)
def reset_activities():
    # reset the in-memory store before each test
    app_module.activities = copy.deepcopy(ORIGINAL_ACTIVITIES)
    yield


@pytest.fixture
def client():
    # use FastAPI TestClient for synchronous HTTP requests
    with TestClient(app) as c:
        yield c


def encode(segment: str) -> str:
    return urllib.parse.quote(segment, safe="")


# ---- basic endpoint validation ------------------------------------------------

def test_root_redirect(client):
    # disable automatic redirect following so we can inspect the raw response
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (307, 302)
    # FastAPI uses 307 by default
    assert resp.headers["location"] == "/static/index.html"


def test_get_activities(client):
    resp = client.get("/activities")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    # sample some expected activities and keys
    assert "Chess Club" in data
    chess = data["Chess Club"]
    assert set(chess.keys()) >= {"description", "schedule", "max_participants", "participants"}


# ---- signup tests --------------------------------------------------------------

def test_signup_happy_path(client):
    email = "new@school.edu"
    activity = "Chess Club"
    resp = client.post(f"/activities/{encode(activity)}/signup?email={encode(email)}")
    assert resp.status_code == 200
    assert "Signed up" in resp.json().get("message", "")

    # check that the participant is actually added
    roster = client.get("/activities").json()[activity]["participants"]
    assert email in roster


def test_signup_duplicate(client):
    activity = "Chess Club"
    existing = ORIGINAL_ACTIVITIES[activity]["participants"][0]
    resp = client.post(f"/activities/{encode(activity)}/signup?email={encode(existing)}")
    assert resp.status_code == 400
    assert "already signed up" in resp.json().get("detail", "").lower()


def test_signup_invalid_activity(client):
    resp = client.post(f"/activities/{encode('Nope')}/signup?email={encode('a@b.c')}")
    assert resp.status_code == 404


# ---- unregister tests ---------------------------------------------------------

def test_unregister_happy_path(client):
    activity = "Chess Club"
    email = ORIGINAL_ACTIVITIES[activity]["participants"][0]
    resp = client.delete(f"/activities/{encode(activity)}/unregister?email={encode(email)}")
    assert resp.status_code == 200
    assert "Unregistered" in resp.json().get("message", "")

    roster = client.get("/activities").json()[activity]["participants"]
    assert email not in roster


def test_unregister_not_registered(client):
    activity = "Chess Club"
    resp = client.delete(f"/activities/{encode(activity)}/unregister?email={encode('none@here')}")
    assert resp.status_code == 400
    assert "not registered" in resp.json().get("detail", "").lower()


def test_unregister_invalid_activity(client):
    resp = client.delete(f"/activities/{encode('Nope')}/unregister?email={encode('a@b.c')}")
    assert resp.status_code == 404
