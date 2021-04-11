from abc import ABC
from enum import Flag, auto

from data.model.external_service import ExternalService


class ExternalServiceFeature(Flag):
    ONLY_STREAMING = auto()
    RECORD_LISTENS = auto()
    BOTH = ONLY_STREAMING & RECORD_LISTENS


class ExternalServiceBase(ABC):

    def __init__(self, service: ExternalService, features: ExternalServiceFeature):
        self.service = service
        self.features = features

    def add_new_user(self, user_id: int, token: dict):
        raise NotImplementedError()

    def remove_user(self, user_id: int):
        raise NotImplementedError()

    def get_user(self, user_id: int):
        raise NotImplementedError()

    def get_features(self) -> ExternalServiceFeature:
        return self.features

    def get_service_type(self) -> ExternalService:
        return self.service

    def get_authorize_url(self, scopes: ExternalServiceFeature):
        raise NotImplementedError()

    def fetch_access_token(self, code):
        raise NotImplementedError()

    def refresh_token(self, user_id):
        raise NotImplementedError()
