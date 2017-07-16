#! /bin/env python
# -- requires 3.6 or higher

import asyncio
import os
import time


class Inspector(object):

    created  = {}
    accessed = {}
    modified = {}
    errors   = {}


    def __init__(self,
            topdir,
            start=None, end=None, window=None,
            report_matches=None, report_errors=None):
        """
        Initialize the class.

        \param   topdir         Directory to begin walking.
        \param   start          Unix timestamp for the start of the time range,
        \param   end            Unix timestamp for the end of the time range,
        \param   window         [optional] instead of start/end, you can provide
                                start+window or end+window and the remaining
                                parameter (end or start) will be calculated.
        \param   report_matches Callable that takes (path, stat) for every
                                file that has a stamp inside the window.
        \param   report_errors  Callable that takes (path, exception) when stat
                                raises an exception.
        """

        if not os.path.exists(topdir):
            raise ValueError("topdir '%s' does not exist." % topdir)
        self.topdir = topdir

        # Sanity check arguments and, if window is provided, modify start/end
        if start is not None and end is not None:
            pass  # Great, you gave me everything I need.
        elif start is not None:
            if window is None:
                raise ArgumentError("start requires end or window")
            end = start + window
        else:   # window can't be None
            if window is None:
                raise ArgumentError("end requires start or window")
            start = end - window

        # If the user gets them the wrong way around, fix it.
        self.start = min(start, end)
        self.end   = max(start, end)

        self.start, self.end = start, end

        self.matchesCb = report_matches
        self.errorCb   = report_errors


    def _propagate(self, dest, path, stamp, dirname=os.path.dirname):
        """
        Internal helper: Touch the directory tree for this path and
        everything above it. E.g if /foo/bar/file.txt is modified,
        apply the timestamp to /foo/bar and /foo. This makes it easier
        to find modifications by following the "max" of any given level.
        """

        while path != "":
            oldval = dest.get(path, -1)
            if stamp < oldval:
                return
            dest[path] = stamp
            path = dirname(path)


    @asyncio.coroutine
    def _stat(self, path, statfn=os.stat):
        """ Async-wrapper around 'stat'. """
        return statfn(path)


    @asyncio.coroutine
    def _check(self, paths):
        """ Check a list of paths against our timeranges. """

        # Minimize lookups.
        start     = self.start
        end       = self.end
        matchCb   = self.matchesCb
        errorCb   = self.errorCb
        addPfx    = self.topdir.__add__
        stat      = self._stat
        propagate = self._propagate

        for path in paths:
            # Stat the file using the absolute path.
            fullpath = addPfx(path)
            try:
                st = yield from asyncio.async(stat(fullpath))
            except (PermissionError, FileNotFoundError) as e:
                self.errors[fullpath] = e
                if errorCb: self.errorCb(fullpath, e)
                continue

            # Strip root directory (and drive on Windows)
            candidate = 0
            if start < st.st_ctime < end:
                propagate(self.created, path, st.st_ctime)
                candidate = st.st_ctime
            if start < st.st_atime < end:
                propagate(self.accessed, path, st.st_atime)
                candidate = st.st_atime if not candidate else candidate
            if start < st.st_mtime < end:
                propagate(self.modified, path, st.st_mtime)
                candidate = st.st_mtime if not candidate else candidate

            if candidate and matchCb:
                matchCb(fullpath, st)


    @asyncio.coroutine
    def inspect(self):
        """
        Descends a directory tree looking for files that were created, modified
        or accessed during a particular time frame.

        See .created, .accessed, .modified and .errors when complete.
        """

        topdirLen = len(self.topdir)
        check     = self._check

        for root, dirs, files in os.walk(self.topdir):
            root = root[topdirLen:] + os.path.sep
            yield from check([root])
            if files:
                yield from check(map(root.__add__, files))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    inspector = Inspector('c:/Users/oliver', end=1500236538, window=180,
                    report_errors=lambda p, e: print(repr(e), p))

    print("- Running", inspector.topdir)
    loop.run_until_complete(inspector.inspect())
    print("- Done")
    print()

    def dump(collection, paths):
        print("#### %s:" % (collection))
        print("#")
        for path in paths.keys().sort(key=lambda k: paths[k], reverse=False):
            print("%s : %s" % (path, time.asctime(paths[path])))
        print()

    dump("Created",  inspector.created)
    dump("Accessed", inspector.accessed)
    dump("Modified", inspector.modified)

