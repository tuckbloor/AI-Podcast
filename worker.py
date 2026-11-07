"""Local research worker; processes queued jobs without blocking the UI."""
from __future__ import annotations
from pathlib import Path
import argparse
import sys
import time
from podcast_workspace import connect, execute_one, interrupt_stale


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--poll-seconds',type=float,default=3)
    args=p.parse_args(argv)
    with connect() as db:
        interrupt_stale(db)
    print('Podcast research worker ready',flush=True)
    while True:
        with connect() as db:
            processed=execute_one(db)
        if not processed:time.sleep(max(0.5,args.poll_seconds))


if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:raise SystemExit(0)
