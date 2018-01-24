# section_ops
Section operation hacks


# Running

    $ ./build.py
    2018-01-24 03:06:23,720 INFO  Loading cache ...
    2018-01-24 03:06:23,721 INFO  Fetching current sections ...
    2018-01-24 03:06:25,931 INFO  +++ Fetched ops (5 entries)
    2018-01-24 03:06:26,951 INFO  +++ Fetched database (8 entries)
    2018-01-24 03:06:28,078 INFO  +++ Fetched internet-of-things (2 entries)
    2018-01-24 03:06:29,132 INFO  +++ Fetched featured (14 entries)
    2018-01-24 03:06:30,332 INFO  +++ Fetched messaging (10 entries)
    2018-01-24 03:06:31,464 INFO  +++ Fetched media (6 entries)
    2018-01-24 03:06:32,601 INFO  +++ Fetched editors (0 entries)
    2018-01-24 03:06:33,607 INFO  +++ Fetched devops (4 entries)
    2018-01-24 03:06:34,738 INFO  +++ Fetched cryptocurrency (8 entries)
    2018-01-24 03:06:35,762 INFO  +++ Fetched games (7 entries)
    2018-01-24 03:06:35,763 INFO  Saving "current.json" ¯\_(ツ)_/¯ ...
    2018-01-24 03:06:35,764 INFO  Processing new sections ...
    2018-01-24 03:06:35,766 INFO  !!! Ignoring # gradio -> private
    2018-01-24 03:06:35,767 INFO  *** Parsing music (11 entries)
    2018-01-24 03:06:35,768 INFO  *** Parsing games (17 entries)
    2018-01-24 03:06:35,769 INFO  !!! Ignoring # freechartgeany -> private
    2018-01-24 03:06:35,769 INFO  *** Parsing finance (14 entries)
    2018-01-24 03:06:35,770 INFO  !!! Ignoring # darktable -> darktable-kyrofa maybe ?
    2018-01-24 03:06:35,771 INFO  *** Parsing graphics (13 entries)
    2018-01-24 03:06:35,771 INFO  *** Parsing utilities (8 entries)
    2018-01-24 03:06:35,771 INFO  !!! Ignoring # kodi -> not in stable
    2018-01-24 03:06:35,772 INFO  !!! Ignoring # plexmediaserver -> menta-plexmediaserver maybe ?
    2018-01-24 03:06:35,772 INFO  *** Parsing video (11 entries)
    2018-01-24 03:06:35,773 INFO  *** Parsing social-networking (16 entries)
    2018-01-24 03:06:35,773 INFO  *** Parsing productivity (17 entries)
    2018-01-24 03:06:35,773 INFO  *** Parsing developers (16 entries)
    2018-01-24 03:06:35,774 INFO  *** Parsing featured (16 entries)
    2018-01-24 03:06:35,774 INFO  Calculating snap deletions ...
    2018-01-24 03:06:35,775 INFO  Saving "delete.json" ...
    2018-01-24 03:06:35,775 INFO  Calculating snap updates ...
    2018-01-24 03:06:35,776 INFO  Saving "update.json" ...
    ========================================================================
    Copy "delete.json" and "update.json" to a snapfind instance. Then run the following commands:

      $ psql <production_dsn> -c "DELETE FROM section WHERE name IN ('cryptocurrency', 'database', 'devops', 'editors', 'internet-of-things', 'media', 'messaging', 'ops');"
      $ curl -X DELETE -H 'Content-Type: application/json' http://localhost:8003/sections/snaps -d '@delete.json'
      $ curl -X POST -H 'Content-Type: application/json' http://localhost:8003/sections/snaps -d '@update.json'

    In case you screwed things up, copy "current.json" to a snapfind instance. Then run the following commands:

      $ psql <production_dsn> -c "DELETE FROM section;"
      $ curl -X POST -H 'Content-Type: application/json' http://localhost:8003/sections/snaps -d '@current.json'
    ========================================================================
    2018-01-24 03:06:35,781 INFO  Saving cache ...
