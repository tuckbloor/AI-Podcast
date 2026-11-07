import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from podcast_workspace import connect, queue_research, claim_next, execute_one, get_run, list_runs, csv_for_run, interrupt_stale
from podcast_agent.models import Podcast

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='podcast data with spaces ')
        self.addCleanup(self.tmp.cleanup)
        self.db=connect(Path(self.tmp.name)/'my research.sqlite3')
        self.addCleanup(self.db.close)

    def test_queues_one_active_run_and_rejects_invalid_requests(self):
        with self.assertRaises(ValueError):queue_research(self.db,'abc')
        ident=queue_research(self.db,'Software engineering podcasts')
        self.assertEqual(ident,queue_research(self.db,'Manufacturing podcasts'))
        self.assertEqual(len(list_runs(self.db)),1)

    def test_worker_runs_agent_and_saves_results(self):
        ident=queue_research(self.db,'Engineering interview podcasts')
        def fake(goal,**kwargs):
            kwargs['progress'](.5,'Checking public podcast feeds')
            kwargs['on_activity']('Found public guest information')
            kwargs['on_status']({'kind':'stage','progress':.9,'message':'Writing drafts'})
            return SimpleNamespace(podcasts=[Podcast('Engineering Weekly','https://feeds.example/rss',score=82)],
                 queries=['engineering'],tool_calls=3,research_errors=0,ollama_requests=1,
                 model_decisions=0,fallback_used=False,uk_only=False,
                 region_excluded=0,rejected_leads=0,suitable_contacts_found=0)
        self.assertTrue(execute_one(self.db,agent=fake))
        run=get_run(self.db,ident)
        self.assertEqual(run['status'],'completed')
        self.assertIn('Engineering Weekly',csv_for_run(run))
        self.assertFalse(execute_one(self.db,agent=fake))

    def test_worker_failure_records_error_and_can_queue_another(self):
        ident=queue_research(self.db,'Manufacturing research podcasts')
        def fail(*a,**k):raise RuntimeError('Offline test failure')
        self.assertTrue(execute_one(self.db,agent=fail))
        self.assertEqual(get_run(self.db,ident)['status'],'failed')
        self.assertNotEqual(ident,queue_research(self.db,'More manufacturing research podcasts'))

    def test_csv_escapes_external_formula_cells(self):
        fake={'results_json':json.dumps([{'Podcast':'=HYPERLINK("evil")','Evidence score':95}])}
        result=csv_for_run(fake)
        self.assertIn("'=HYPERLINK",result)

    def test_interrupted_run_does_not_silently_retry(self):
        ident=queue_research(self.db,'Software engineering research podcasts')
        claim_next(self.db)
        interrupt_stale(self.db)
        self.assertEqual(get_run(self.db,ident)['status'],'interrupted')

if __name__=='__main__':unittest.main()
