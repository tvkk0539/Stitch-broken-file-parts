
import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
from app.managers.github_tool import GitHubManager

class TestGitHubRouting(unittest.TestCase):

    @patch('app.managers.github_tool.config.load_config')
    @patch('app.managers.github_tool.GitHubManager._fetch_user_profile')
    @patch('app.managers.github_tool.GitHubManager._get_token_for_account')
    @patch('app.managers.github_tool.GitHubManager.get_repo_details')
    @patch('app.managers.github_tool.GitHubManager.create_repository')
    @patch('app.managers.github_tool.requests.post')
    @patch('app.managers.github_tool.requests.get')
    @patch('app.managers.github_tool.os.path.getsize')
    @patch('builtins.open', new_callable=mock_open, read_data=b"data")
    def test_smart_publish_routing_map(self, mock_file, mock_size, mock_get, mock_post, mock_create, mock_details, mock_token, mock_profile, mock_load):
        # Setup Config
        mock_load.return_value = {
            'github_accounts': [
                {'id': '1', 'username': 'user1'},
                {'id': '2', 'username': 'user2'}
            ]
        }

        # Setup Mocks
        mock_token.return_value = 'fake_token'
        mock_profile.return_value = {'username': 'user1'}

        # Mock Repo Details (Always exists/empty)
        mock_details.return_value = {'size': 1024} # 1MB

        # Mock File Size (1GB)
        mock_size.return_value = 1 * 1024 * 1024 * 1024

        # Mock API Responses
        # Release Create
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 201
        mock_post_resp.json.return_value = {
            'upload_url': 'https://uploads.github.com/repos/user/repo/releases/1/assets{?name,label}',
            'html_url': 'https://github.com/user/repo/releases/tag/v1'
        }

        # Upload Asset
        mock_post_resp_upload = MagicMock()
        mock_post_resp_upload.status_code = 201
        mock_post_resp_upload.json.return_value = {
            'browser_download_url': 'https://github.com/user/repo/releases/download/v1/file.rar'
        }

        # Side Effect for Post (First call release, subsequent uploads)
        mock_post.side_effect = [mock_post_resp, mock_post_resp_upload, mock_post_resp_upload]

        # Inputs
        files = ['/tmp/file1.rar', '/tmp/file2.rar']
        dist_map = [
            {'account_id': '1', 'repo': 'user1/repoA'},
            {'account_id': '2', 'repo': 'user2/repoB'}
        ]

        # Run
        res = GitHubManager.smart_publish_job(
            files=files,
            base_repo_name='backup', # Should be ignored
            tag='v1',
            account_id='1', # Should be ignored
            distribution_map=dist_map,
            strict_mode=True
        )

        # Assertions
        self.assertIn('assets', res)
        self.assertEqual(len(res['assets']), 2)

        # Verify Routing
        # We mocked 2 files.
        # Strict mode doesn't force a switch unless limit is hit.
        # 1GB file < 45GB limit. So both should go to Account 1 if sequential.
        # Wait, smart_publish_job uses 'relay' (sequential) by default.
        # So both files should go to user1/repoA.

        self.assertEqual(res['assets'][0]['account_id'], '1')
        self.assertEqual(res['assets'][0]['repo'], 'user1/repoA')
        self.assertEqual(res['assets'][1]['account_id'], '1') # Still 1

    @patch('app.managers.github_tool.config.load_config')
    @patch('app.managers.github_tool.GitHubManager._fetch_user_profile')
    @patch('app.managers.github_tool.GitHubManager._get_token_for_account')
    @patch('app.managers.github_tool.GitHubManager.get_repo_details')
    @patch('app.managers.github_tool.GitHubManager.create_repository')
    @patch('app.managers.github_tool.requests.post')
    @patch('app.managers.github_tool.os.path.getsize')
    @patch('builtins.open', new_callable=mock_open, read_data=b"data")
    def test_smart_publish_strict_mode_switch(self, mock_file, mock_size, mock_post, mock_create, mock_details, mock_token, mock_profile, mock_load):
        # Setup Config
        mock_load.return_value = {
            'github_accounts': [
                {'id': '1', 'username': 'user1'},
                {'id': '2', 'username': 'user2'}
            ]
        }

        mock_token.return_value = 'fake_token'
        mock_profile.side_effect = [{'username': 'user1'}, {'username': 'user2'}] # Calls for each acc

        # Mock Repo Details
        # First call (Acc 1): Returns 44GB used (Close to limit)
        # Second call (Acc 2): Returns 0GB used
        mock_details.side_effect = [
            {'size': 44 * 1024 * 1024}, # 44GB in KB (KB is size unit in list_repos but get_details returns size in KB usually)
            {'size': 0}
        ]

        # Mock File Size (2GB)
        # 44 + 2 = 46 > 45. Should switch.
        mock_size.return_value = 2 * 1024 * 1024 * 1024

        # Mock API
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 201
        mock_post_resp.json.return_value = {
            'upload_url': 'https://url',
            'html_url': 'https://url'
        }
        mock_post.return_value = mock_post_resp

        files = ['/tmp/huge_file.rar']
        dist_map = [
            {'account_id': '1', 'repo': 'user1/repoA'},
            {'account_id': '2', 'repo': 'user2/repoB'}
        ]

        res = GitHubManager.smart_publish_job(
            files=files,
            base_repo_name='backup',
            tag='v1',
            account_id='1',
            distribution_map=dist_map,
            strict_mode=True
        )

        # Verify it switched to Account 2
        self.assertEqual(len(res['assets']), 1)
        self.assertEqual(res['assets'][0]['account_id'], '2')
        self.assertEqual(res['assets'][0]['repo'], 'user2/repoB')

if __name__ == '__main__':
    unittest.main()
