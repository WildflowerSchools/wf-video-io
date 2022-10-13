set dotenv-load := true
version := "v9"


lint:
    pylint video_io


build-docker-migrate:
    @docker build -t wildflowerschools/wf-classroom-video-store:migrate-{{version}} -f migrate/Dockerfile .
    @docker push wildflowerschools/wf-classroom-video-store:migrate-{{version}}
