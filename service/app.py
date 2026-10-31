"""HTTP-сервис рекомендаций (FastAPI).

Запуск:  uvicorn service.app:app --reload --port 8000     Документация: http://localhost:8000/docs
"""
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi import Path as PathParam

ARTIFACTS_DIR = Path(os.environ.get('ARTIFACTS_DIR', 'artifacts'))
K = 3
state = {}


def recommend_items(user_top, popular, user_id, k=K):
    """Свои товары пользователя, затем популярные без повторов; всего k."""
    items = list(user_top.get(user_id, []))
    for item_id in popular:
        if len(items) >= k:
            break
        if item_id not in items:
            items.append(item_id)
    return items


@asynccontextmanager
async def lifespan(app):
    try:
        raw = json.loads((ARTIFACTS_DIR / 'user_top.json').read_text(encoding='utf-8'))
        state['user_top'] = {int(u): items for u, items in raw.items()}          # ключи JSON - строки, возвращаем числа
        state['popular'] = json.loads((ARTIFACTS_DIR / 'popular.json').read_text(encoding='utf-8'))
        state['metrics'] = json.loads((ARTIFACTS_DIR / 'metrics.json').read_text(encoding='utf-8'))
    except FileNotFoundError as error:
        state['error'] = f'не найден файл артефактов: {error.filename}'
    yield
    state.clear()


app = FastAPI(title='Recommender service', version='1.0.0', lifespan=lifespan)


def require_model():
    if 'user_top' not in state:
        raise HTTPException(status_code=503, detail=state.get('error', 'модель не загружена'))


@app.get('/health')
def health():
    require_model()
    return {'status': 'ok', 'users_in_model': len(state['user_top']), 'popular_items': len(state['popular'])}


@app.get('/metrics')
def metrics():
    require_model()
    return state['metrics']


@app.get('/recommend/{user_id}')
def recommend(user_id: int = PathParam(..., ge=0, description='visitorid - неотрицательное целое')):
    require_model()
    items = recommend_items(state['user_top'], state['popular'], user_id)
    return {'user_id': user_id, 'items': items,
            'source': 'personal' if user_id in state['user_top'] else 'popular'}
