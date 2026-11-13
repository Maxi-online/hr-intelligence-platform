from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Добавляем родительскую директорию в путь для импорта shared модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import HealthResponse, RankingRequest, RankingResponse, RankingWeights, Candidate, SearchRequest
from shared.utils import setup_logging

logger = setup_logging("ranking-service")

app = FastAPI(
    title="Ranking Service",
    description="Сервис ранжирования кандидатов (AI-first)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Храним веса в памяти для обратной совместимости UI/интеграций
current_weights = RankingWeights()


def sort_by_ai_score(candidates: List[Candidate]) -> List[Candidate]:
    # Сортировка по полю score (AI-оценка), если нет — 0.0
    return sorted(candidates, key=lambda c: (c.score or 0.0), reverse=True)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", timestamp=datetime.now(), version="1.0.0")


@app.post("/rank", response_model=RankingResponse)
async def rank_candidates(request: RankingRequest):
    try:
        ranked = sort_by_ai_score(request.candidates)
        # Минимальные метаданные: просто фиксируем распределение скоров
        scores = [c.score or 0.0 for c in ranked]
        metadata = {
            "total_candidates": len(ranked),
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "weights_used": (request.weights or current_weights).model_dump(),
        }
        return RankingResponse(ranked_candidates=ranked, ranking_metadata=metadata)
    except Exception as e:
        logger.error(f"Ошибка ранжирования: {e}")
        raise HTTPException(status_code=500, detail="Ошибка ранжирования")


@app.get("/weights")
async def get_weights():
    try:
        return {"weights": current_weights.model_dump()}
    except Exception as e:
        logger.error(f"Ошибка получения весов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения весов")


@app.put("/weights")
async def update_weights(weights: RankingWeights):
    try:
        global current_weights
        current_weights = weights
        return {"message": "Веса обновлены"}
    except Exception as e:
        logger.error(f"Ошибка обновления весов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления весов")


@app.post("/calculate-scores")
async def calculate_scores(request: RankingRequest):
    try:
        # В AI-first архитектуре считаем, что score уже проставлен мультиагентной системой.
        # Для обратной совместимости возвращаем входные кандидаты и простую метаинформацию.
        return {
            "candidates": [c.model_dump() for c in request.candidates],
            "metadata": {"note": "AI-first: базовые баллы уже заданы в поле score"}
        }
    except Exception as e:
        logger.error(f"Ошибка расчета баллов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка расчета баллов")


if __name__ == "__main__":
    import uvicorn
    from shared.utils import load_config
    config = load_config()
    service_config = config.get("services", {}).get("ranking", {})
    uvicorn.run(
        app,
        host=service_config.get("host", "0.0.0.0"),
        port=service_config.get("port", 8002),
        reload=service_config.get("debug", False)
    )

