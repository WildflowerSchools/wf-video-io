import concurrent.futures
import json
import os
from pathlib import Path
import re
import subprocess
from typing import List, Dict

from auth0.v3.management.users import Users
from auth0.v3.management.clients import Clients
from auth0.v3.authentication import GetToken
from cachetools.func import ttl_cache
from jose import jwt
import jmespath
import requests
from tenacity import retry, wait_random, stop_after_attempt


class SyncError(Exception):
    pass


class RequestError(Exception):

    def __init__(self, response):
        super().__init__(f"unexpected api response - {response.status_code}")
        self.response = response



class UnableToAuthenticate(Exception):
    pass



AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN")
API_AUDIENCE = os.environ.get("API_AUDIENCE")
CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID")
CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET")
VIDEO_STORAGE_LOCAL_CACHE_DIRECTORY = os.environ.get("VIDEO_STORAGE_LOCAL_CACHE_DIRECTORY", "/data")
MAX_SYNC_WORKERS = os.environ.get("MAX_SYNC_WORKERS", 10)
VIDEO_STORAGE_URL = os.environ.get("VIDEO_STORAGE_URL", "https://video.api.wildflower-tech.org")


@ttl_cache(ttl=60 * 60 * 4)
def client_token(audience=None):
    get_token = GetToken(AUTH0_DOMAIN, timeout=10)
    token = get_token.client_credentials(
        CLIENT_ID,
        CLIENT_SECRET,
        audience if audience is not None else API_AUDIENCE)
    api_token = token['access_token']
    return api_token

@ttl_cache(ttl=60 * 60 * 4)
def get_video_file_details(path):
    ffprobe_out = subprocess.run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=nb_read_frames,r_frame_rate,codec_type",
        "-count_frames",
        "-of",
        "json=compact=1",
        path,
    ], capture_output=True)
    return json.loads(ffprobe_out.stdout)


def client_from_honeycomb_settings(client=None, token_uri=None, audience=None, client_id=None, client_secret=None):
    if client is not None:
        token = client.client.accessToken
    elif client_id is not None and client_secret is not None:
        get_token = GetToken(AUTH0_DOMAIN, timeout=10)
        response = get_token.client_credentials(
            client_id,
            client_secret,
            audience if audience is not None else API_AUDIENCE)
        token = response['access_token']
    else:
        token = client_token(audience)
    return VideoStorageClient(token)


CACHE_PATH_FILE = re.compile('^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/(?P<hour>[0-9]{2})/(?P<file>.*)$')
CACHE_PATH_HOUR = re.compile('^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/(?P<hour>[0-9]{2})$')
CACHE_PATH_DAY = re.compile('^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})$')
CACHE_PATH_MONTH = re.compile('^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})$')
CACHE_PATH_YEAR = re.compile('^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)/(?P<year>[0-9]{4})$')
CACHE_PATH_CAM = re.compile('^(?P<environment_id>[a-fA-F0-9-]*)/(?P<camera_id>[a-fA-F0-9-]*)$')

FPS_PATH = jmespath.compile("streams[?codec_type=='video'].r_frame_rate")

def parse_path(path: str) -> (str, dict):
    result = ('none', None)
    for name, pattern in [
        ('file', CACHE_PATH_FILE,),
        ('hour', CACHE_PATH_HOUR,),
        ('day', CACHE_PATH_DAY,),
        ('month', CACHE_PATH_MONTH,),
        ('year', CACHE_PATH_YEAR,),
        ('camera', CACHE_PATH_CAM,),
    ]:
        match = pattern.match(path)
        if match:
            result = (name, match.groupdict())
            continue
    return result


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class VideoStorageClient:

    def __init__(self, token=None):
        self.DOMAIN = VIDEO_STORAGE_URL
        if token is not None:
            self.token = token
        else:
            self.token = client_token()

    async def get_videos(self, environment_id, start_date, end_date, camera_id=None, destination=None):
        prefix = destination if destination is not None else VIDEO_STORAGE_LOCAL_CACHE_DIRECTORY
        os.makedirs(prefix, exist_ok=True)
        meta = self.get_videos_metadata_paginated(environment_id, start_date, end_date, camera_id)
        async for vid_meta in meta:
            await self.get_video(vid_meta["meta"]["path"], destination)

    async def get_video(self, path, destination):
        request = {
            "method": "GET",
            "url": f'{self.DOMAIN}/video/{path}',
            "headers": {
                "Authorization": f"bearer {self.token}",
            },
        }
        response = requests.request(**request)
        if response.status_code == 200:
            p = Path(destination).joinpath(path)
            pp = p.parent
            if not pp.exists():
                pp.mkdir(parents=True, exist_ok=True)
            p.write_bytes(response.content)


    async def get_videos_metadata_paginated(self, environment_id, start_date, end_date, camera_id=None, skip=0, limit=100):
        current_skip = skip
        while True:
            page = await self.get_videos_metadata(environment_id, start_date, end_date, camera_id=camera_id, skip=current_skip, limit=limit)
            for item in page:
                yield item
            current_skip += limit
            if len(page) == 0:
                break

    async def get_videos_metadata(self, environment_id, start_date, end_date, camera_id=None, skip=0, limit=100):
        request = {
            "method": "GET",
            "url": f'{self.DOMAIN}/videos/{environment_id}/{camera_id}' if camera_id is not None else f'{self.DOMAIN}/videos/{environment_id}',
            "headers": {
                "Authorization": f"bearer {self.token}",
            },
            "params": {
                "start_date": start_date,
                "end_date": end_date,
                "skip": skip,
                "limit": limit,
            }
        }
        response = requests.request(**request)
        if response.status_code == 200:
            data = response.json()
            return data
        raise RequestError(response)


    async def upload_video(self, path, local_cache_directory=None):
        prefix = local_cache_directory if local_cache_directory is not None else VIDEO_STORAGE_LOCAL_CACHE_DIRECTORY
        full_path = os.path.join(prefix, path)
        ptype, file_details = parse_path(path)
        if ptype == "file":
            file_details["path"] = full_path
            file_details["filepath"] = full_path[len(prefix):]
            resp =  await self.upload_videos([file_details])
            return resp[0]
        return {"error": "invalid path. doesn't match pattern [environment_id]/[camera_id]/[year]/[month]/[day]/[hour]/[min]-[second].mp4"}

    @retry(wait=wait_random(min=1, max=5), stop=stop_after_attempt(7))
    async def upload_videos(self, file_details: List[Dict]):
        request = {
            "method": "POST",
            "url": f"{self.DOMAIN}/videos",
            "headers": {
                "Authorization": f"bearer {self.token}",
            }
        }
        files = []
        videos = []
        for details in file_details:
            path = details["path"]
            files.append(("files", open(path, 'rb'), ))
            video_properties = get_video_file_details(path)
            videos.append(dict(
                timestamp=f"{details['year']}-{details['month']}-{details['day']}T{details['hour']}:{details['file'][0:2]}:{details['file'][3:5]}.0000",
                meta=dict(
                    environment_id=details["environment_id"],
                    assignment_id=None,
                    camera_id=details["camera_id"],
                    duration_seconds=video_properties["format"]["duration"],
                    fps=eval(FPS_PATH.search(video_properties)[0]),
                    path=details["filepath"],
                ),
            ))
        results = []
        request["files"] = files
        request["data"] = {"videos": json.dumps(videos)}
        request = requests.Request(**request)
        r = request.prepare()
        s = requests.Session()
        response = s.send(r)
        for i, vr in enumerate(response.json()):
            results.append({"path": videos[i]['meta']['path'], "uploaded": True, "id": vr["id"], "disposition": "ok" if "disposition" not in vr else vr["disposition"]})
        return results

    @retry(wait=wait_random(min=1, max=5), stop=stop_after_attempt(7))
    async def video_existence_check(self, paths: List[str]):
        request = {
            "method": "POST",
            "url": f"{self.DOMAIN}/videos/check",
            "headers": {
                "Authorization": f"bearer {self.token}",
            },
            "json": paths,
        }
        r = requests.Request(**request).prepare()
        s = requests.Session()
        response = s.send(r)
        try:
            return response.json()
        except Exception as e:
            print(response.text)
            return [{"err": "response error", "path": p, "exists": False} for p in paths]


    async def upload_videos_in(self, path, local_cache_directory=None, batch_size=4):
        t, details = parse_path(path[:-1] if path[-1] == '/' else path)
        if details:
            if t == "file":
                raise SyncError("didn't expect file, expected directory, try `upload_video`")
            if t == "year":
                raise SyncError("cannot sync a year of videos, try limiting to a day")
            if t == "month":
                raise SyncError("cannot sync a month of videos, try limiting to a day")
            files_found = []
            prefix = local_cache_directory if local_cache_directory is not None else VIDEO_STORAGE_LOCAL_CACHE_DIRECTORY
            for root, _, files in os.walk(os.path.join(prefix, path)):
                for file in files:
                    full_path = os.path.join(root, file)
                    ptype, file_details = parse_path(full_path[len(prefix):])
                    if ptype == "file":
                        file_details["path"] = full_path
                        file_details["filepath"] = full_path[len(prefix):]
                        files_found.append(file_details)
            details["files_found"] = len(files_found)
            details["files_uploaded"] = 0
            details["details"] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_SYNC_WORKERS) as executor:
                results = executor.map(self.upload_videos, chunks(files_found, batch_size))
                for future in results:
                    result = await future
                    for data in result:
                        if data["uploaded"]:
                            details["files_uploaded"] += 1
                        details["details"].append(data)
            return details
        raise SyncError("path {path} was not parsable")
