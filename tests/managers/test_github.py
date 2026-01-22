
import unittest
from unittest.mock import patch, MagicMock
from app.managers.github_tool import GitHubManager
from app.core import config

class TestGitHubManager(unittest.TestCase):

    @patch('app.managers.github_tool.config.load_config')
    @patch('app.managers.github_tool.config.save_config')
    @patch('app.managers.github_tool.requests.get')
    def test_add_account_success(self, mock_get, mock_save, mock_load):
        # Setup mocks
        mock_load.return_value = {'github_accounts': []}

        # Mock GitHub API response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'id': 12345,
            'login': 'testuser',
            'name': 'Test User',
            'avatar_url': 'http://avatar.url'
        }
        mock_get.return_value = mock_resp

        # Call method
        result = GitHubManager.add_account('fake_token')

        # Assertions
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['username'], 'testuser')

        # Verify save called with correct structure
        mock_save.assert_called_once()
        saved_conf = mock_save.call_args[0][0]
        self.assertEqual(len(saved_conf['github_accounts']), 1)
        self.assertEqual(saved_conf['github_accounts'][0]['token'], 'fake_token')

    @patch('app.managers.github_tool.config.load_config')
    @patch('app.managers.github_tool.config.save_config')
    def test_remove_account(self, mock_save, mock_load):
        # Setup existing account
        mock_load.return_value = {
            'github_accounts': [{'id': '123', 'username': 'user1'}]
        }

        # Remove it
        res = GitHubManager.remove_account('123')
        self.assertEqual(res['status'], 'removed')

        # Verify empty list saved
        saved_conf = mock_save.call_args[0][0]
        self.assertEqual(len(saved_conf['github_accounts']), 0)

    @patch('app.managers.github_tool.config.load_config')
    def test_list_accounts_hides_token(self, mock_load):
        mock_load.return_value = {
            'github_accounts': [{'id': '1', 'username': 'u', 'token': 'secret'}]
        }

        accounts = GitHubManager.list_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertNotIn('token', accounts[0])
        self.assertEqual(accounts[0]['username'], 'u')

    @patch('app.managers.github_tool.config.load_config')
    @patch('app.managers.github_tool.requests.get')
    def test_list_user_repos(self, mock_get, mock_load):
        mock_load.return_value = {
            'github_accounts': [{'id': '1', 'token': 'secret'}]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{'full_name': 'user/repo', 'private': False}]
        mock_get.return_value = mock_resp

        repos = GitHubManager.list_user_repos('1')
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]['name'], 'user/repo')

    @patch('app.managers.github_tool.config.load_config')
    @patch('app.managers.github_tool.requests.patch')
    def test_update_repo_visibility(self, mock_patch, mock_load):
        mock_load.return_value = {
            'github_accounts': [{'id': '1', 'token': 'secret'}]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'private': True}
        mock_patch.return_value = mock_resp

        res = GitHubManager.update_repo_visibility('user/repo', True, '1')
        self.assertEqual(res['status'], 'success')
        self.assertTrue(res['private'])

if __name__ == '__main__':
    unittest.main()
