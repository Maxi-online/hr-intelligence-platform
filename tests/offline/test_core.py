import unittest
from pydantic import ValidationError
from offline_demo import run, Candidate, RankingRequest, SearchRequest

class HRContractTests(unittest.TestCase):
    def test_score_order(self): self.assertEqual(run()["candidate_ids"],["demo-2","demo-1","demo-3"])
    def test_missing_required_candidate_fields(self):
        with self.assertRaises(ValidationError):Candidate(id="demo")
    def test_search_defaults(self):self.assertEqual(SearchRequest(text="Python").page,1)
    def test_empty_batch_contract(self):self.assertEqual(RankingRequest(candidates=[],search_request=SearchRequest()).candidates,[])
