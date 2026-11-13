"""Validate the real CandidateRanking schemas and existing score ordering on synthetic profiles."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).parent/"components/candidate_ranking"))
from shared.models import Candidate, RankingRequest, SearchRequest
from ranking.main import sort_by_ai_score

def run():
    common={"title":"Python engineer","area":{"id":"demo","name":"Synthetic city"},"experience":{"months":36},"updated_at":datetime(2026,1,1,tzinfo=timezone.utc),"url":"https://example.invalid/resume"}
    candidates=[Candidate(id="demo-1",score=0.3,**common),Candidate(id="demo-2",score=0.9,**common),Candidate(id="demo-3",**common)]
    request=RankingRequest(candidates=candidates,search_request=SearchRequest(text="Python"))
    return {"mode":"synthetic-schema-and-existing-score-ordering","candidate_ids":[c.id for c in sort_by_ai_score(request.candidates)],"new_ai_scores_generated":False,"cross_component_integration_verified":False}
if __name__=="__main__": print(json.dumps(run(),indent=2))
