import unittest
from unittest.mock import patch, MagicMock
from actions import system, apps, volume, media

class TestActions(unittest.TestCase):

    @patch('actions.system.ctypes.windll.user32.LockWorkStation')
    def test_lock_screen(self, mock_lock):
        system.lock_screen()
        mock_lock.assert_called_once()

    @patch('actions.apps.subprocess.Popen')
    def test_open_app_alias(self, mock_popen):
        config = {
            "app_aliases": {"notepad": "notepad.exe"}
        }
        res = apps.open_app("notepad", config)
        self.assertTrue(res)
        mock_popen.assert_called_once_with("notepad.exe")

    @patch('actions.apps.psutil.process_iter')
    def test_close_app(self, mock_process_iter):
        mock_proc = MagicMock()
        mock_proc.info = {'name': 'notepad.exe'}
        mock_process_iter.return_value = [mock_proc]
        
        res = apps.close_app("notepad")
        self.assertTrue(res)
        mock_proc.terminate.assert_called_once()

    @patch('actions.media.keyboard.send')
    def test_media_controls(self, mock_send):
        media.play_pause()
        mock_send.assert_called_with("play/pause media")
        
        media.next_track()
        mock_send.assert_called_with("next track")

if __name__ == '__main__':
    unittest.main()
