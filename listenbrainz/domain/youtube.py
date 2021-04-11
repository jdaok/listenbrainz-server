from datetime import timezone

from data.model.external_service import ExternalService
from listenbrainz.db import external_service as db_service

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from listenbrainz.domain.service import ExternalServiceBase, ExternalServiceFeature


class YoutubeService(ExternalServiceBase):
    youtube_scopes = ("https://www.googleapis.com/auth/youtube.readonly",)

    def __init__(self, config, redirect_uri):
        super(YoutubeService, self).__init__(ExternalService.YOUTUBE, ExternalServiceFeature.ONLY_STREAMING)
        self.client_config = config
        self.redirect_uri = redirect_uri

    def get_authorize_url(self, feature: ExternalServiceFeature):
        flow = Flow.from_client_config(self.client_config,
                                       scopes=self.youtube_scopes,
                                       redirect_uri=self.redirect_uri)

        authorization_url, _ = flow.authorization_url(access_type="offline",
                                                      include_granted_scopes="true")
        return authorization_url

    def fetch_access_token(self, code):
        flow = Flow.from_client_config(self.client_config,
                                       scopes=self.youtube_scopes,
                                       redirect_uri=self.redirect_uri)
        token = flow.fetch_token(code=code)
        return token

    def refresh_token(self, user_id):
        client = self.client_config["web"]
        user = self.get_user(user_id)
        credentials = Credentials(token=user["access_token"], refresh_token=user["refresh_token"],
                                  client_id=client["client_id"], client_secret=client["client_secret"],
                                  token_uri=client["token_uri"], scopes=self.youtube_scopes,
                                  expiry=user["token_expires"])

        credentials.refresh(Request())
        db_service.update_token(user_id=user_id, service=ExternalService.YOUTUBE, access_token=credentials.token,
                                refresh_token=credentials.refresh_token,
                                expires_at=int(credentials.expiry.replace(tzinfo=timezone.utc).timestamp()))

        return self.get_user(user_id)

    def add_new_user(self, user_id, token: dict):
        db_service.save_token(user_id=user_id, service=ExternalService.YOUTUBE, access_token=token["access_token"],
                              refresh_token=token["refresh_token"], token_expires_ts=int(token["expires_at"]),
                              record_listens=False, service_details={"scopes": token["scope"]})

    def remove_user(self, user_id):
        db_service.delete_token(user_id=user_id, service=ExternalService.YOUTUBE)

    def get_user(self, user_id):
        return db_service.get_token(user_id=user_id, service=ExternalService.YOUTUBE)
