set dotenv-load := true
version := "v9"


lint:
    pylint video_io

format:
    black video_io

publish:
    poetry publish --username ${PYPI_USERNAME} --password ${PYPI_PASSWORD} --skip-existing


build-docker-migrate:
    @docker build -t wildflowerschools/wf-classroom-video-store:migrate-{{version}} -f migrate/Dockerfile .
    @docker push wildflowerschools/wf-classroom-video-store:migrate-{{version}}
