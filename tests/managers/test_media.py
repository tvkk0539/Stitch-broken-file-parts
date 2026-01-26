import unittest
import os
import shutil
from unittest.mock import patch, MagicMock
from app.managers.media import MediaManager

class TestMediaManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_media_extract"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

        # Create dummy audio files
        self.audio_file = os.path.join(self.test_dir, "song.mp3")
        with open(self.audio_file, 'w') as f: f.write("dummy audio")

        self.sub_dir = os.path.join(self.test_dir, "album")
        os.makedirs(self.sub_dir)
        self.sub_audio = os.path.join(self.sub_dir, "track.flac")
        with open(self.sub_audio, 'w') as f: f.write("dummy flac")

        # Existing cover
        self.existing_cover_audio = os.path.join(self.test_dir, "existing.mp3")
        with open(self.existing_cover_audio, 'w') as f: f.write("dummy")
        self.existing_cover = os.path.join(self.test_dir, "existing.jpg")
        with open(self.existing_cover, 'w') as f: f.write("existing image")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('app.managers.media.subprocess.run')
    def test_run_extract_covers_job(self, mock_run):
        # Mock successful ffmpeg run
        # We need to mock os.path.exists and os.path.getsize for the verification step inside process_file
        # But process_file checks real filesystem.
        # So we can't easily mock the RESULT of ffmpeg unless we actually create the file.

        # However, we can verify that subprocess.run was CALLED with correct args.

        # Setup mock return
        mock_run.return_value = MagicMock(returncode=0)

        paths = [self.test_dir]
        MediaManager.run_extract_covers_job(paths)

        # Verify calls
        # 1. song.mp3 -> song.jpg
        expected_song_jpg = os.path.join(self.test_dir, "song.jpg")
        # 2. album/track.flac -> album/track.jpg
        expected_track_jpg = os.path.join(self.sub_dir, "track.jpg")

        # We expect subprocess calls
        # args: ['ffmpeg', '-nostdin', '-i', input, '-an', output]

        calls = mock_run.call_args_list
        cmd_inputs = [c[0][0][3] for c in calls] # 4th arg is input path
        cmd_outputs = [c[0][0][5] for c in calls] # 6th arg is output path

        self.assertIn(self.audio_file, cmd_inputs)
        self.assertIn(expected_song_jpg, cmd_outputs)

        self.assertIn(self.sub_audio, cmd_inputs)
        self.assertIn(expected_track_jpg, cmd_outputs)

        # Check that existing cover was skipped
        self.assertNotIn(self.existing_cover_audio, cmd_inputs)

if __name__ == '__main__':
    unittest.main()
