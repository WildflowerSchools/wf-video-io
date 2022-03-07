Feature: Client for interacting with the service

  Scenario: Cache-path operations
  Given a set of paths and their expected results
   | environment_id                       | camera_id                            | year | month | day | hour | matches | cache_path                                                                                        |
   | a44cb30b-3107-4dad-8a86-3a0f17c36cb3 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 1000 | 04    | 01  | 03   | file    | a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/1000/04/01/03/00-00.mp4 |
   | a44cb30b-3107-4dad-8a86-3a0f17c36cb3 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 2022 | 12    | 12  | 02   | hour    | a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/2022/12/12/02           |
   | a44cb30b-3107-4dad-8a86-3a0f17c36cb3 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 2022 | 12    | 12  |      | day     | a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/2022/12/12              |
   | a44cb30b-3107-4dad-8a86-3a0f17c36cb3 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 2022 | 12    |     |      | month   | a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/2022/12                 |
   | a44cb30b-3107-4dad-8a86-3a0f17c36cb3 | 6e3631ac-815a-49c4-8038-51e1909a9662 | 1000 |       |     |      | year    | a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/1918                    |
   | a44cb30b-3107-4dad-8a86-3a0f17c36cb3 | 6e3631ac-815a-49c4-8038-51e1909a9662 |      |       |     |      | camera  | a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662                         |
   |                                      |                                      |      |       |     |      | none    | a44cb30b-3107-4dad-8a86-3h0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/2000/1                  |
   |                                      |                                      |      |       |     |      | none    | a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/2000/3/09               |
  Then all should pass

  Scenario: Client video upload
  Given the directory `features/test-data/` as the cache path
  and a clean database
  When requesting to upload_videos_in `a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/1000/04/01/`
  Then 10 files should be found
  and 10 files should be uploaded


  Scenario: Get video metadata
  Given the directory `features/test-data/` as the cache path
  and a clean database
  When requesting to upload_videos_in `a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/1000/04/01/`
  and requesting video metadata for `a44cb30b-3107-4dad-8a86-3a0f17c36cb3` 1000-04-01T00:00:00.000-0000 to 1000-04-01T05:00:00.000-0000
  Then 10 video should be returned

  Scenario: Attempt to upload existing video, single
  Given the directory `features/test-data/` as the cache path
  and a the path `a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/1000/04/01/08/00-01.mp4` to upload
  and a clean database
  When requesting to upload the video
  Then the request returns the metadata with the id
  When requesting to upload the video
  Then request returns a video-exists disposition


  Scenario: Load up some videos then download to a different location
  Given the directory `features/test-data/` as the cache path
  and the destination path `features/local-test/` that is empty
  and a clean database
  When requesting to upload_videos_in `a44cb30b-3107-4dad-8a86-3a0f17c36cb3/6e3631ac-815a-49c4-8038-51e1909a9662/1000/04/01/`
  and requesting videos for `a44cb30b-3107-4dad-8a86-3a0f17c36cb3` 1000-04-01T00:00:00.000-0000 to 1000-04-02T00:00:00.000-0000
  Then 10 video files should be in the destination
