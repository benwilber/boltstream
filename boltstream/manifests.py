import logging
from datetime import timedelta
from os.path import basename

from furl import furl
from m3u8 import M3U8, Media, Playlist, Segment
from m3u8 import load as load_m3u8

logger = logging.getLogger(__name__)


def make_master_manifest(request, stream):
    if stream.info:
        bandwidth = int(stream.info["bw_out"])
        width = stream.info["meta"]["video"]["width"]
        height = stream.info["meta"]["video"]["height"]
        stream_info = {
            "bandwidth": bandwidth,
            "resolution": f"{width}x{height}",
            "codecs": "avc1.640028,mp4a.40.2",
        }
    else:
        stream_info = {"bandwidth": 1000}

    p = Playlist(basename(stream.index_manifest_url), stream_info, None, None)
    m = M3U8()
    m.add_playlist(p)

    for feed in stream.feeds.all():
        media = Media(
            type="SUBTITLES",
            group_id="feeds",
            name=f"feed-{feed.uuid}",
            language="en",
            default="YES",
            autoselect="YES",
            uri=furl(feed.manifest_url).set({"stream": stream.uuid}).url,
        )
        p.media.append(media)
        m.add_media(media)

    return m.dumps()


def make_feed_manifest(request, stream, feed):
    url = request.build_absolute_uri(stream.index_manifest_url)
    p = load_m3u8(url)
    m = M3U8()
    m.version = p.version
    m.target_duration = p.target_duration
    m.media_sequence = p.media_sequence
    for s in p.segments:
        if not m.program_date_time:
            m.program_date_time = s.current_program_date_time

        vtt_url = furl(basename(feed.webvtt_url)).set({"stream": stream.uuid})
        if s.current_program_date_time:
            vtt_url.args.update(
                {
                    "start": s.current_program_date_time.isoformat(),
                    "end": (
                        s.current_program_date_time + timedelta(seconds=s.duration)
                    ).isoformat(),
                    "epoch": stream.started_at.isoformat(),
                }
            )
        v = Segment(
            base_uri=vtt_url.url,
            uri=vtt_url.url,
            duration=s.duration,
            discontinuity=s.discontinuity,
            program_date_time=s.current_program_date_time,
        )
        m.add_segment(v)

    return m.dumps()
