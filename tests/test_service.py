import importlib
import json

import pytest

pytest.importorskip('fastapi')
pytest.importorskip('httpx')
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    (tmp_path / 'user_top.json').write_text(json.dumps({'7': [11, 12, 13], '8': [11]}))
    (tmp_path / 'popular.json').write_text(json.dumps([100, 101, 102, 103]))
    (tmp_path / 'metrics.json').write_text(json.dumps({'precision_at_3_test_personal': 0.03}))
    monkeypatch.setenv('ARTIFACTS_DIR', str(tmp_path))
    import service.app as app_module
    importlib.reload(app_module)                       # заново читаем ARTIFACTS_DIR
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_health(client):
    assert client.get('/health').json()['status'] == 'ok'


def test_known_user(client):
    assert client.get('/recommend/7').json() == {'user_id': 7, 'items': [11, 12, 13], 'source': 'personal'}


def test_short_history_is_padded_with_popular(client):
    assert client.get('/recommend/8').json()['items'] == [11, 100, 101]


def test_unknown_user_gets_popular(client):
    body = client.get('/recommend/999999').json()
    assert body['items'] == [100, 101, 102] and body['source'] == 'popular'


@pytest.mark.parametrize('bad', ['abc', '-5', '1.5'])
def test_invalid_user_id_is_422(client, bad):
    assert client.get(f'/recommend/{bad}').status_code == 422


def test_metrics(client):
    assert client.get('/metrics').json()['precision_at_3_test_personal'] == 0.03
