#!/usr/bin/env python3
"""
Increment ./state and commit the next days.

This is for hacking the github commit graph
"""

import os
from datetime import datetime, timedelta

ISO8601 = '%Y-%m-%dT%H:%M:%S%z'
PATH = './state'
DAYS = 1000
EPOCH = datetime.strptime('2000-01-01T00:00:00Z', ISO8601)

def read_state():
    """Return the last day commited."""
    with open(PATH) as state:
        line = state.read().strip()
        return datetime.strptime(line, ISO8601)


def commit_day(when):
    """Commit one day."""
    value = when.strftime(ISO8601)

    with open(PATH, 'w') as state:
        state.seek(0)
        state.write(value + '\n')
        state.close()

    os.system('git commit -q -m "commit %s" --date %s state' % (value, value))


def main():
    when = read_state()
    print('commiting %i days starting %s' % (DAYS, when))
    for d in range(DAYS):
        when += timedelta(days=1)
        di = (when - EPOCH).days
        if di % 2 == 0:
            commit_day(when)
            commit_day(when + timedelta(hours=12))
        else:
            commit_day(when)

    print('done: committed up to %s' % when)


if __name__ == '__main__':
    main()
