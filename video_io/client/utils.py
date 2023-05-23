import json
import re
import subprocess

import ffmpeg
from tenacity import retry, wait_random, stop_after_attempt
from auth0.v3.authentication import GetToken
from cachetools.func import ttl_cache
import jmespath


@ttl_cache(ttl=60 * 60 * 4)
def is_v2_directory(path):
    index_file = path / "wf-video-index.yml"
    return index_file.exists()


@ttl_cache(ttl=60 * 60 * 4)
@retry(wait=wait_random(min=1, max=3), stop=stop_after_attempt(7))
def client_token(
    auth_domain, audience, client_id=None, client_secret=None
) -> (str, int):
    get_token = GetToken(auth_domain, timeout=10)
    token = get_token.client_credentials(client_id, client_secret, audience)
    api_token = token["access_token"]
    expires_in = token["expires_in"]
    return api_token, expires_in


@ttl_cache(ttl=60 * 60 * 4)
def get_video_file_details(path):
    # check for video file if it exists load that and return its contents.
    # if not then run ffprobe and return a new meta document
    return ffmpeg.probe(path, timeout=5)


CACHE_PATH_FILE = re.compile(
    "^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/(?P<hour>[0-9]{2})/(?P<file>.*)$"
)
CACHE_PATH_HOUR = re.compile(
    "^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/(?P<hour>[0-9]{2})$"
)
CACHE_PATH_DAY_V2 = re.compile(
    "^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})$"
)
CACHE_PATH_FILE_V2 = re.compile(
    "^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})/(?P<file>.*)$"
)
CACHE_PATH_DAY = re.compile(
    "^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})$"
)
CACHE_PATH_MONTH = re.compile(
    "^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})$"
)
CACHE_PATH_YEAR = re.compile(
    "^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})$"
)
CACHE_PATH_CAM = re.compile(
    "^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)$"
)
CACHE_PATH_ENV = re.compile("^(?P<environment_id>[a-fA-F0-9-]*)$")

FPS_PATH = jmespath.compile("streams[?codec_type=='video'].r_frame_rate")


def parse_path(path: str) -> (str, dict):
    result = ("none", None)
    for name, pattern in [
        (
            "fileV2",
            CACHE_PATH_FILE_V2,
        ),
        (
            "dayV2",
            CACHE_PATH_DAY_V2,
        ),
        (
            "file",
            CACHE_PATH_FILE,
        ),
        (
            "hour",
            CACHE_PATH_HOUR,
        ),
        (
            "day",
            CACHE_PATH_DAY,
        ),
        (
            "month",
            CACHE_PATH_MONTH,
        ),
        (
            "year",
            CACHE_PATH_YEAR,
        ),
        (
            "camera",
            CACHE_PATH_CAM,
        ),
        (
            "environment",
            CACHE_PATH_ENV,
        ),
    ]:
        match = pattern.match(path)
        if match:
            result = (name, match.groupdict())
            continue
    return result


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
