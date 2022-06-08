import os
import multiprocessing
import datetime

VIDEO_DURATION = datetime.timedelta(seconds=10)

VIDEO_STORAGE_URL = os.environ.get('VIDEO_STORAGE_URL', 'https://video.api.wildflower-tech.org')

VIDEO_STORAGE_AUTH_DOMAIN = os.environ.get('VIDEO_STORAGE_AUTH_DOMAIN', os.environ.get('AUTH0_DOMAIN'))
VIDEO_STORAGE_TOKEN_URI = os.environ.get('VIDEO_STORAGE_TOKEN_URI', os.environ.get('AUTH0_TOKEN_URI'))
VIDEO_STORAGE_AUDIENCE = os.environ.get('VIDEO_STORAGE_AUDIENCE', os.environ.get('API_AUDIENCE'))
VIDEO_STORAGE_CLIENT_ID = os.environ.get('VIDEO_STORAGE_CLIENT_ID', os.environ.get('AUTH0_CLIENT_ID'))
VIDEO_STORAGE_CLIENT_SECRET = os.environ.get('VIDEO_STORAGE_CLIENT_SECRET', os.environ.get('AUTH0_CLIENT_SECRET'))

HONEYCOMB_URI = os.environ.get('HONEYCOMB_URI')

HONEYCOMB_AUTH_DOMAIN = os.environ.get('HONEYCOMB_AUTH_DOMAIN', os.environ.get('AUTH0_DOMAIN'))
HONEYCOMB_TOKEN_URI = os.environ.get('HONEYCOMB_TOKEN_URI', os.environ.get('AUTH0_TOKEN_URI'))
HONEYCOMB_AUDIENCE = os.environ.get('HONEYCOMB_AUDIENCE', os.environ.get('API_AUDIENCE'))
HONEYCOMB_CLIENT_ID = os.environ.get('HONEYCOMB_CLIENT_ID', os.environ.get('AUTH0_CLIENT_ID'))
HONEYCOMB_CLIENT_SECRET = os.environ.get('HONEYCOMB_CLIENT_SECRET', os.environ.get('AUTH0_CLIENT_SECRET'))

VIDEO_STORAGE_LOCAL_CACHE_DIRECTORY = os.environ.get('VIDEO_STORAGE_LOCAL_CACHE_DIRECTORY', '/data')

SYNC_BATCH_SIZE = 4
MAX_SYNC_WORKERS = os.environ.get('MAX_SYNC_WORKERS', os.environ.get('MAX_WORKERS', multiprocessing.cpu_count() - 1))

MAX_DOWNLOAD_WORKERS = os.environ.get('MAX_DOWNLOAD_WORKERS', os.environ.get('MAX_WORKERS', multiprocessing.cpu_count() - 1))
