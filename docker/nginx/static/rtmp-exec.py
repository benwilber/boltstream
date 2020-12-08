#!/usr/bin/env python3
import os
import shlex
import sys
from os.path import exists, join as pathjoin
from glob import glob
from shutil import rmtree
from argparse import ArgumentParser
from datetime import datetime, timezone
from subprocess import Popen


def live_publish_done(webroot, name):
    for part in ("live", "keys"):
        try:
            rmtree(pathjoin(webroot, part, name))
        except FileNotFoundError:
            pass

    for ext in ("mp4", "flv"):
        rootdir = pathjoin(webroot, "record")
        for path in glob(f"{rootdir}/{name}*_thumb.{ext}"):
            os.remove(path)


def thumb_record_done(webroot, name, path):
    cmd = (
        f"ffmpeg -hide_banner -v quiet -y -i '{path}' "
        f"-movflags +faststart -an -c:v copy '{webroot}/record/{name}_thumb.mp4'"
    )

    with open(os.devnull, "wb") as f:
        Popen(shlex.split(cmd), stdout=f, stderr=f).wait()

    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def vod_record_done(webroot, name, path):
    rootdir = pathjoin(webroot, "vod", name)
    try:
        os.mkdir(rootdir)
    except FileExistsError:
        pass

    utcnow = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    cmd = (
        f"ffmpeg -hide_banner -v quiet -y -i '{path}' -c copy '{rootdir}/{utcnow}.mp4'"
    )

    with open(os.devnull, "wb") as f:
        Popen(shlex.split(cmd), stdout=f, stderr=f).wait()

    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def main():
    parser = ArgumentParser(description="RTMP exec actions")
    parser.add_argument("-w", "--webroot", required=True)
    parser.add_argument("-e", "--event", required=True)
    parser.add_argument("-n", "--name", required=True)
    parser.add_argument("-p", "--path")
    args = parser.parse_args()

    if args.event in ("thumb_record_done", "vod_record_done") and not args.path:
        print("-p/--path is required", file=sys.stderr)
        sys.exit(os.EX_USAGE)

    if args.event == "live_publish_done":
        live_publish_done(args.webroot, args.name)
    elif args.event == "thumb_record_done":
        thumb_record_done(args.webroot, args.name, args.path)
    elif args.event == "vod_record_done":
        vod_record_done(args.webroot, args.name, args.path)
    else:
        print(f"unknown event {args.event}", file=sys.stderr)
        sys.exit(os.EX_USAGE)


if __name__ == "__main__":
    main()
