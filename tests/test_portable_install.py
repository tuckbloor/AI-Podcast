from pathlib import Path
import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('podcast_install',ROOT/'tools/podcast_install.py')
installer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class PortableInstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='Podcast Install With Spaces ')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.server=self.root/'App Server Prerequisite'
        self.podcast=self.root/'Podcast Instance'

    def test_full_source_has_two_bat_files_and_correct_version(self):
        installer.validate_source()
        self.assertEqual(installer.VERSION,'1.1.0-rc1')
        self.assertEqual({x.name for x in ROOT.rglob('*.bat')},{'INSTALL.bat','START.bat'})
        self.assertTrue((ROOT/'README.md').is_file())
        self.assertFalse((ROOT/'app.py').exists())

    def test_fresh_separate_install_no_fixed_drive(self):
        installer.run_pipeline(server=self.server,podcast=self.podcast,
              install_new_server=True,copy_only=True,log=lambda _:None)
        self.assertTrue((self.server/'engine/pyproject.toml').is_file())
        self.assertTrue((self.podcast/'app/app.py').is_file())
        self.assertTrue((self.podcast/'podcast_agent/agent.py').is_file())
        self.assertFalse((self.server/'data/podcast-outreach.sqlite3').exists())
        self.assertFalse((self.podcast/'data/podcast-outreach.sqlite3').exists())
        self.assertTrue(installer.recognized_podcast(self.podcast))

    def test_existing_server_not_modified(self):
        installer.install_server(self.server,copy_only=True)
        (self.server/'app').mkdir()
        (self.server/'app/app.py').write_text('# present')
        ex=installer.python_for(self.server)
        ex.parent.mkdir(parents=True,exist_ok=True);ex.write_text('simulated environment')
        before={p.relative_to(self.server):p.read_bytes() for p in self.server.rglob('*') if p.is_file()}
        installer.run_pipeline(server=self.server,podcast=self.podcast,
            install_new_server=False,copy_only=True,log=lambda _:None)
        after={p.relative_to(self.server):p.read_bytes() for p in self.server.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_unrelated_folder_cannot_be_overwritten(self):
        self.podcast.mkdir();(self.podcast/'private.txt').write_text('untouched')
        with self.assertRaises(installer.InstallError):
            installer.install_podcast(self.podcast,copy_only=True,allow_update=True)
        self.assertEqual((self.podcast/'private.txt').read_text(),'untouched')

    def test_confirmed_update_preserves_database_and_backup(self):
        installer.install_podcast(self.podcast,copy_only=True)
        (self.podcast/'data').mkdir()
        db=self.podcast/'data/podcast-outreach.sqlite3';db.write_bytes(b'original user database')
        (self.podcast/'podcast_workspace.py').write_text('# old original code')
        with self.assertRaises(installer.InstallError):
            installer.install_podcast(self.podcast,copy_only=True)
        installer.install_podcast(self.podcast,copy_only=True,allow_update=True)
        self.assertEqual(db.read_bytes(),b'original user database')
        self.assertTrue(list((self.podcast/'backups').rglob('podcast_workspace.py')))
        self.assertIn('Private, persistent job queue',(self.podcast/'podcast_workspace.py').read_text())

    def test_update_rollback_when_dependency_install_fails(self):
        installer.install_podcast(self.podcast,copy_only=True)
        db=self.podcast/'data/podcast-outreach.sqlite3'
        db.parent.mkdir();db.write_bytes(b'private data')
        original=self.podcast/'podcast_workspace.py';original.write_text('# previous version')
        with patch.object(installer,'python_for',return_value=self.podcast/'fake-python'):
            (self.podcast/'fake-python').write_text('stub')
            with patch.object(installer,'run',side_effect=installer.InstallError('simulated pip failure')):
                with self.assertRaises(installer.InstallError):
                    installer.install_podcast(self.podcast,copy_only=False,allow_update=True)
        self.assertEqual(original.read_text(),'# previous version')
        self.assertEqual(db.read_bytes(),b'private data')

    def test_separate_directories_required(self):
        with self.assertRaises(installer.InstallError):
            installer.validate_paths(self.server,self.server)
        with self.assertRaises(installer.InstallError):
            installer.validate_paths(self.server,self.server/'Nested')

if __name__=='__main__':unittest.main()
