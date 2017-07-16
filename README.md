# tsinspector
Timestamp Inspector 

##
Description

Python script that will walk a directory tree to find files that have
timestamps (created, accessed, modified) within a given timeframe. It is a
finessed version of what you might do with the "find . -ctime" command,
for example, and the information exists in Python for inspection.

##
Requirements

Python 3.6 or higher with asyncio.coroutines

#
Example Use

```
# Check the current working directory and below for files
# that have been manipulated in the last 10 minutes.
import asyncio, os, time

import tsinspector
inspector = tsinspector.Inspector(
        topdir=os.getcwd(),   # Path to crawl
        end=time.time(),      # High end of the timeframe
        window=10*60,         # Scan for a 10 minute window
        report_errors=lambda path, err: print(repr(err), path)
        )
loop = asyncio.get_event_loop()
loop.run_until_complete(inspector.inspect())
# loop.close() if you aren't using it any more.

# Files created during the window
print(inspector.created)

# Files accessed during the window
print(inspector.accessed)

# Files modifie during the window
print(inspector.modified)
```
