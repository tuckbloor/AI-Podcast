"""Exercise both Streamlit page paths with a minimal offline renderer shim."""
import runpy
import sys
import types
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from podcast_agent.agent import ResearchRun
from podcast_agent.models import Podcast


class Widget:
    def __init__(self):
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def empty(self):
        return self

    def metric(self, *a, **kw):
        return None

    def progress(self, *a, **kw):
        return None

    def markdown(self, *a, **kw):
        return None

    def caption(self, *a, **kw):
        return None

    def info(self, *a, **kw):
        return None

    def warning(self, *a, **kw):
        return None

    def success(self, *a, **kw):
        return None


class StreamlitAppSmokeTests(unittest.TestCase):
    def fake_streamlit(self, submitted=False):
        fake = types.ModuleType('streamlit')
        fake.session_state = {}
        fake.cache_data = lambda **kwargs: (lambda fn: fn)
        fake.sidebar = Widget()
        fake.form = lambda *a, **k: Widget()
        fake.expander = lambda *a, **k: Widget()
        fake.empty = lambda: Widget()
        fake.progress = lambda *a, **k: Widget()
        fake.columns = lambda n: [Widget() for _ in range(n)]
        fake.text_area = lambda *a, **k: 'software developer in the uk only'
        fake.form_submit_button = lambda *a, **k: submitted
        fake.selectbox = lambda name, options, **k: options[0]
        fake.slider = lambda *a, **k: 8
        for action in ('set_page_config', 'title', 'header', 'caption', 'markdown', 'write', 'info',
                       'success', 'error', 'warning', 'divider', 'subheader', 'dataframe', 'download_button'):
            setattr(fake, action, lambda *a, **k: None)
        return fake

    def execute(self, submitted=False):
        fake = self.fake_streamlit(submitted=submitted)
        project = Path(__file__).resolve().parents[1]
        result = ResearchRun(podcasts=[Podcast('Test UK Podcast', 'https://example.com/rss',
                                              description='UK-based show', score=80,
                                              outreach_intro='Hello, would you be open to a guest collaboration?')],
                             queries=['UK software developers'], tool_calls=3)
        def runner(*a, **kwargs):
            kwargs['progress'](0.15, 'Searching Apple Podcasts')
            kwargs['on_activity']('1.0s · Apple search test: one result')
            kwargs['on_status']({'kind': 'start'})
            kwargs['on_status']({'kind': 'chunk', 'chunks': 8, 'elapsed': 0.4})
            kwargs['on_status']({'kind': 'retry', 'reason': 'bad first batch'})
            kwargs['on_status']({'kind': 'done', 'chunks': 8, 'elapsed': 0.8})
            return result
        with patch.dict(sys.modules, {'streamlit': fake}), patch('podcast_agent.ai.installed_models', return_value=['llama3.2:3b']), patch('podcast_agent.agent.run_agent', side_effect=runner):
            # app.py imports symbols directly, so runpy re-imports them from patched modules
            runpy.run_path(str(project / 'app.py'), run_name='__main__')
        return fake

    def test_original_screen_opens_without_submitting(self):
        fake = self.execute(False)
        self.assertNotIn('results', fake.session_state)

    def test_research_renders_progress_and_results_without_widget_errors(self):
        fake = self.execute(True)
        self.assertEqual(len(fake.session_state.get('results', [])), 1)
        self.assertEqual(fake.session_state.get('agent_stats', {}).get('Research tool calls'), 3)


if __name__ == '__main__':
    unittest.main()
