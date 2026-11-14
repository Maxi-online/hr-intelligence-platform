from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add the parent directory to the route to import the used modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import HealthResponse, RankingRequest, RankingResponse, RankingWeights, Candidate, SearchRequest
from shared.utils import setup_logging

logger = setup_logging("ranking-service")

app = FastAPI(
    title="Ranking Service",
    description="Candidates' ranking service (AI-first)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Weight storage in memory for reverse UI/integration compatibility
current_weights = RankingWeights()


def sort_by_ai_score(candidates: List[Candidate]) -> List[Candidate]:
    # Sorting field Score (AI-estimate) if not 0.0
    return sorted(candidates, key=lambda c: (c.score or 0.0), reverse=True)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", timestamp=datetime.now(), version="1.0.0")


@app.post("/rank", response_model=RankingResponse)
async def rank_candidates(request: RankingRequest):
    try:
        ranked = sort_by_ai_score(request.candidates)
        # Minimum metadata: just record the speed distribution
        scores = [c.score or 0.0 for c in ranked]
        metadata = {
            "total_candidates": len(ranked),
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "weights_used": (request.weights or current_weights).model_dump(),
        }
        return RankingResponse(ranked_candidates=ranked, ranking_metadata=metadata)
    except Exception as e:
        logger.error(f"Error of ranking: {e}")
        raise HTTPException(status_code=500, detail='Error of ranking')


@app.get("/weights")
async def get_weights():
    try:
        return {"weights": current_weights.model_dump()}
    except Exception as e:
        logger.error(f"Error to gain weight: {e}")
        raise HTTPException(status_code=500, detail='Error to gain weight')


@app.put("/weights")
async def update_weights(weights: RankingWeights):
    try:
        global current_weights
        current_weights = weights
        return {"message": 'Weights updated'}
    except Exception as e:
        logger.error(f"Error of Weight Update: {e}")
        raise HTTPException(status_code=500, detail='Error of Weight Update')


@app.post("/calculate-scores")
async def calculate_scores(request: RankingRequest):
    try:
        # In AI-first architecture, we believe that the score is already running the multi-agent system.
        # For interoperability, return entry candidates and simple meta-information.
        return {
            "candidates": [c.model_dump() for c in request.candidates],
            "metadata": {"note": 'AI-first: Basic points already set in score field'}
        }
    except Exception as e:
        logger.error(f"Error in calculating points: {e}")
        raise HTTPException(status_code=500, detail='Error in calculating points')


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

