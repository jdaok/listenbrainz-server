import time
from datetime import datetime

import requests_mock

from flask import current_app

from listenbrainz.domain import spotify
from listenbrainz.domain.spotify import SpotifyService
from listenbrainz.webserver.testing import ServerTestCase
from unittest import mock


class SpotifyDomainTestCase(ServerTestCase):

    def setUp(self):
        super(SpotifyDomainTestCase, self).setUp()
        self.spotify_user = spotify.Spotify(
                user_id=1,
                musicbrainz_id='spotify_user',
                musicbrainz_row_id=312,
                user_token='old-token',
                token_expires=datetime.now(),
                token_expired=False,
                refresh_token='old-refresh-token',
                last_updated=None,
                record_listens=True,
                error_message=None,
                latest_listened_at=None,
                permission='user-read-recently-played',
            )

    # apparently, requests_mocker does not follow the usual order in which decorators are applied. :-(
    @requests_mock.Mocker()
    @mock.patch('listenbrainz.domain.spotify.db_spotify.get_user')
    @mock.patch('listenbrainz.domain.spotify.db_spotify.update_token')
    def test_refresh_user_token(self, mock_requests, mock_update_token, mock_db_get_user):
        expires_at = int(time.time()) + 3600
        mock_requests.post(spotify.OAUTH_TOKEN_URL, status_code=200, json={
            'access_token': 'tokentoken',
            'refresh_token': 'refreshtokentoken',
            'expires_in': 3600,
            'scope': '',
        })

        mock_db_get_user.return_value = {
            'user_id': 1,
            'musicbrainz_id': 'spotify_user',
            'musicbrainz_row_id': 312,
            'user_token': 'token-token-token',
            'token_expires': datetime.now(),
            'token_expired': True,
            'refresh_token': 'refresh-refresh-refresh',
            'last_updated': None,
            'record_listens': True,
            'error_message': 'oops',
            'latest_listened_at': None,
            'permission': 'user-read-recently-played',
        }

        SpotifyService().refresh_token(self.spotify_user.user_id)
        mock_update_token.assert_called_with(
            self.spotify_user.user_id,
            'tokentoken',
            'refreshtokentoken',
            expires_at,
        )
        mock_db_get_user.assert_called_with(self.spotify_user.user_id)

    @requests_mock.Mocker()
    @mock.patch('listenbrainz.domain.spotify.db_spotify.get_user')
    @mock.patch('listenbrainz.domain.spotify.db_spotify.update_token')
    def test_refresh_user_token_only_access(self, mock_requests, mock_update_token, mock_db_get_user):
        mock_requests.post(spotify.OAUTH_TOKEN_URL, status_code=200, json={
            'access_token': 'tokentoken',
            'expires_in': 3600,
            'scope': '',
        })

        mock_db_get_user.return_value = {
            'user_id': 1,
            'musicbrainz_id': 'spotify_user',
            'musicbrainz_row_id': 312,
            'user_token': 'token-token-token',
            'token_expires': int(time.time()),
            'token_expired': True,
            'refresh_token': 'refresh-refresh-refresh',
            'last_updated': None,
            'record_listens': True,
            'error_message': 'oops',
            'latest_listened_at': None,
            'permission': 'user-read-recently-played',
        }

        SpotifyService().refresh_token(self.spotify_user.user_id)
        mock_update_token.assert_called_with(
            self.spotify_user.user_id,
            'tokentoken',
            'refresh-refresh-refresh',
            mock.ANY  # expires_at cannot be accurately calculated hence using mock.ANY
            # another option is using a range for expires_at and a Matcher but that seems far more work
        )
        mock_db_get_user.assert_called_with(self.spotify_user.user_id)

    @requests_mock.Mocker()
    def test_refresh_user_token_bad(self, mock_requests):
        mock_requests.post(spotify.OAUTH_TOKEN_URL, status_code=400, json={
            'error': 'invalid request',
            'error_description': 'invalid refresh token',
        })
        with self.assertRaises(spotify.SpotifyAPIError):
            SpotifyService().refresh_token(self.spotify_user.user_id)

    # apparently, requests_mocker does not follow the usual order in which decorators are applied. :-(
    @requests_mock.Mocker()
    def test_refresh_user_token_revoked(self, mock_requests):
        mock_requests.post(spotify.OAUTH_TOKEN_URL, status_code=400, json={
            'error': 'invalid_grant',
            'error_description': 'Refresh token revoked',
        })
        with self.assertRaises(spotify.SpotifyInvalidGrantError):
            SpotifyService().refresh_token(self.spotify_user.user_id)

    @mock.patch('listenbrainz.domain.spotify.db_spotify.get_user')
    def test_get_user(self, mock_db_get_user):
        t = datetime.now()
        expected_user = {
            'user_id': 1,
            'musicbrainz_id': 'spotify_user',
            'musicbrainz_row_id': 312,
            'user_token': 'token-token-token',
            'token_expires': t,
            'token_expired': False,
            'refresh_token': 'refresh-refresh-refresh',
            'last_updated': None,
            'record_listens': True,
            'error_message': 'oops',
            'latest_listened_at': None,
            'permission': 'user-read-recently-played',
        }
        mock_db_get_user.return_value = expected_user
        expected_user['access_token'] = expected_user['user_token']

        user = SpotifyService().get_user(1)
        self.assertDictEqual(expected_user, user)

    @mock.patch('listenbrainz.domain.spotify.db_spotify.delete_spotify')
    def test_remove_user(self, mock_delete):
        SpotifyService().remove_user(1)
        mock_delete.assert_called_with(1)

    @mock.patch('listenbrainz.domain.spotify.db_spotify.create_spotify')
    @mock.patch('listenbrainz.domain.spotify.time.time')
    def test_add_new_user(self, mock_time, mock_create):
        mock_time.return_value = 0
        SpotifyService().add_new_user(1, {
            'access_token': 'access-token',
            'refresh_token': 'refresh-token',
            'expires_in': 3600,
            'scope': '',
        })
        mock_create.assert_called_with(1, 'access-token', 'refresh-token', 3600, False, '')

    @mock.patch('listenbrainz.domain.spotify.db_spotify.get_active_users_to_process')
    def test_get_active_users(self, mock_get_active_users):
        t = int(time.time())
        mock_get_active_users.return_value = [
            {
                'user_id': 1,
                'musicbrainz_id': 'spotify_user',
                'musicbrainz_row_id': 312,
                'user_token': 'token-token-token',
                'token_expires': t,
                'token_expired': False,
                'refresh_token': 'refresh-refresh-refresh',
                'last_updated': None,
                'record_listens': True,
                'error_message': 'oops',
                'latest_listened_at': None,
                'permission': 'user-read-recently-played',
            },
            {
                'user_id': 2,
                'musicbrainz_id': 'spotify_user_2',
                'musicbrainz_row_id': 321,
                'user_token': 'token-token-token321',
                'token_expires': t + 31,
                'token_expired': False,
                'refresh_token': 'refresh-refresh-refresh321',
                'last_updated': None,
                'record_listens': True,
                'error_message': 'oops2',
                'latest_listened_at': None,
                'permission': 'user-read-recently-played',
            },
        ]

        lst = spotify.get_active_users_to_process()
        mock_get_active_users.assert_called_once()
        self.assertEqual(len(lst), 2)
        self.assertIsInstance(lst[0], spotify.Spotify)
        self.assertIsInstance(lst[1], spotify.Spotify)
        self.assertEqual(lst[0].user_id, 1)
        self.assertEqual(lst[1].user_id, 2)

    @mock.patch('listenbrainz.domain.spotify.db_spotify.update_latest_listened_at')
    def test_update_latest_listened_at(self, mock_update_listened_at):
        t = int(time.time())
        SpotifyService().update_latest_listened_at(1, t)
        mock_update_listened_at.assert_called_once_with(1, t)
