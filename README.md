# section_ops
Section operation hacks


# Running

    $ ./build.py
    2018-03-01 04:03:01,651 INFO  Loading cache ...
    2018-03-01 04:03:01,652 INFO  Processing new sections ...
    2018-03-01 04:03:01,653 INFO  *** Parsing music (10 entries)
    2018-03-01 04:03:01,653 INFO  *** Parsing games (16 entries)
    2018-03-01 04:03:01,654 INFO  *** Parsing finance (14 entries)
    2018-03-01 04:03:01,654 INFO  !!! Ignoring # freechartgeany -> private
    2018-03-01 04:03:01,654 INFO  *** Parsing graphics (13 entries)
    2018-03-01 04:03:01,655 INFO  *** Parsing utilities (11 entries)
    2018-03-01 04:03:01,655 INFO  *** Parsing video (11 entries)
    2018-03-01 04:03:01,655 INFO  !!! Ignoring # kodi -> not in stable
    2018-03-01 04:03:01,656 INFO  !!! Ignoring # plexmediaserver -> menta-plexmediaserver and is private
    2018-03-01 04:03:01,656 INFO  *** Parsing social-networking (16 entries)
    2018-03-01 04:03:01,656 INFO  *** Parsing productivity (21 entries)
    2018-03-01 04:03:01,657 INFO  *** Parsing developers (16 entries)
    2018-03-01 04:03:01,657 INFO  *** Parsing featured (16 entries)
    2018-03-01 04:03:01,658 INFO  Calculating snap updates ...
    2018-03-01 04:03:01,658 INFO  Saving "update.json" ...
    2018-03-01 04:03:01,660 INFO  Calculating snap deletions ...
    2018-03-01 04:03:01,661 INFO  No deletions needed.
    ========================================================================
    Copy "delete.json" and "update.json" to a snapfind instance. Then run the following commands:

      $ curl -X POST -H 'Content-Type: application/json' http://localhost:8003/sections/snaps -d '@update.json'

    In case you screwed things up, copy "current.json" to a snapfind instance. Then run the following commands:

      $ psql <production_dsn> -c "DELETE FROM section;"
      $ curl -X POST -H 'Content-Type: application/json' http://localhost:8003/sections/snaps -d '@current.json'
    ========================================================================
    2018-03-01 04:03:01,663 INFO  Saving cache ...
