import os
from pathlib import Path
import shutil

from behave import *
from behave.api.async_step import async_run_until_complete
import pymongo

import video_io.client

@given(u'a clean database')
def step_impl(context):
    host = os.environ.get("WF_MONGODB_HOST")
    if host not in ["localhost", "127.0.0.1"]:
        raise Exception("possible unsafe operation. Mongo should be local. Are you sure you are running against a clean test Database?")
    client = pymongo.MongoClient(
        host,
    )
    db = client.video_storage
    db.video_meta.delete_many({})


@given(u'an environment_id of `{environment_id}`')
def step_impl(context, environment_id):
    context.environment_id = environment_id


@given(u'a set of paths and their expected results')
def step_impl(context):
    results = []
    for item in context.table:
        results.append((item, video_io.client.parse_path(item["cache_path"]), ))
    context.results = results

@then(u'all should pass')
def step_impl(context):
    for item, result in context.results:
        print(result)
        print(item)
        assert item["matches"] == result[0]



@given(u'the directory `{directory}` as the cache path')
def step_impl(context, directory):
    video_io.client.VIDEO_STORAGE_LOCAL_CACHE_DIRECTORY = directory
    context.client = video_io.client.VideoStorageClient()


@when(u'requesting to upload_videos_in `{path}`')
@async_run_until_complete
async def step_impl(context, path):
    upload_receipt = await context.client.upload_videos_in(path)
    assert upload_receipt is not None
    assert upload_receipt["environment_id"] == "a44cb30b-3107-4dad-8a86-3a0f17c36cb3"
    assert upload_receipt["camera_id"] == "6e3631ac-815a-49c4-8038-51e1909a9662"
    context.upload_receipt = upload_receipt



@then(u'{count} files should be found')
def step_impl(context, count):
    assert context.upload_receipt["files_found"] == int(count)


@then(u'{count} files should be uploaded')
def step_impl(context, count):
    assert context.upload_receipt["files_uploaded"] == int(count)


@when(u'requesting video metadata for `{environment_id}` {start_date} to {end_date}')
@async_run_until_complete
async def step_impl(context, environment_id, start_date, end_date):
    context.videos = await context.client.get_videos_metadata(environment_id, start_date, end_date)

@then(u'{num} video should be returned')
def step_impl(context, num):
    print(f"{num}, {len(context.videos)}")
    assert len(context.videos) == int(num)


@given(u'a the path `{path}` to upload')
def step_impl(context, path):
    context.video_path = path


@when(u'requesting to upload the video')
@async_run_until_complete
async def step_impl(context):
    context.response = await context.client.upload_video(context.video_path)


@then(u'the request returns the metadata with the id')
def step_impl(context):
    assert "id" in context.response

@then(u'request returns a video-exists disposition')
def step_impl(context):
    assert context.response['disposition'] == 'video-exists'


@given(u'the destination path `{destination}` that is empty')
def step_impl(context, destination):
    context.destination = destination
    path = Path(destination)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    elif not path.is_dir():
        raise Exception("destination is not a directory")
    else:
        shutil.rmtree(destination)

@when(u'requesting videos for `{environment_id}` {start_date} to {end_date}')
@async_run_until_complete
async def step_impl(context, environment_id, start_date, end_date):
    await context.client.get_videos(environment_id, start_date, end_date, destination=context.destination)


@then(u'{count} video files should be in the destination')
def step_impl(context, count):
    path = Path(context.destination)
    files = list(path.glob("**/*.mp4"))
    print(files)
    assert len(files) == int(count)
