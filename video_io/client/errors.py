class SyncError(Exception):
    pass


class RequestError(Exception):
    def __init__(self, response):
        super().__init__(f"unexpected api response - {response.status_code}")
        self.response = response


class UnableToAuthenticate(Exception):
    pass
