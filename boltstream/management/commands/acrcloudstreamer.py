import logging
import socket
import struct
import time
from multiprocessing import Process
from queue import Queue
from threading import Event, Thread

import acrcloud_stream_decode
from django.core.management import BaseCommand

from boltstream import acrcloud
from boltstream.models import Stream

logger = logging.getLogger(__name__)


class DecodeWorker(Thread):
    def __init__(self, stream, channel, queue):
        super().__init__()
        self.daemon = True
        self.stream = stream
        self.channel = channel
        self.queue = queue
        self.stopped = Event()

    def stop(self):
        self.stopped.set()

    def run(self):
        params = {
            "callback_func": self.decode_callback,
            "stream_url": self.channel["url"],
            "read_size_sec": 2,  # Fingerprint interval
            "program_id": -1,  # In-stream program ID
            "open_timeout_sec": 10,  # Download timeout
            "read_timeout_sec": 10,  # DOwnload timeout
            "is_debug": 0,
        }

        while not self.stopped.is_set():
            try:
                code, message = acrcloud_stream_decode.decode_audio(params)
            except Exception as e:
                logger.exception(e)
            else:
                if code == 0:
                    self.stop()
                else:
                    logger.error(
                        f"stream={self.stream.uuid}, code={code}, message={message}"
                    )

            time.sleep(1.0)

    def decode_callback(self, is_video, buf):
        if self.stopped.is_set():
            return 1

        self.queue.put(buf)
        return 0


class FingerprintWorker(Thread):
    def __init__(self, stream, channel, queue):
        super().__init__()
        self.daemon = True
        self.stream = stream
        self.channel = channel
        self.queue = queue
        self.stopped = Event()

        self.sample_const = 16000  # ???
        self.fingerprint_time = 6
        self.fingerprint_max_time = 12
        self.fingerprint_interval = 2
        self.doc_pre_time = self.fingerprint_time - self.fingerprint_interval  # ???
        self.upload_timeout = 10

    def stop(self):
        self.stopped.set()

    def run(self):
        last_buf = b""

        while not self.stopped.is_set():
            live_upload = True
            buf = self.queue.get()
            cur_buf = last_buf + buf
            last_buf = cur_buf

            fingerprint = acrcloud_stream_decode.create_fingerprint(cur_buf, False)

            if fingerprint:
                try:
                    self.upload_fingerprint(fingerprint)
                except Exception as e:
                    logger.exception(e)
                    live_upload = False
                    if len(last_buf) > self.fingerprint_max_time * self.sample_const:
                        start = (
                            len(last_buf)
                            - self.fingerprint_max_time * self.sample_const
                        )
                        last_buf = last_buf[start:]

            if live_upload and len(last_buf) > self.doc_pre_time * self.sample_const:
                idx = -1 * self.doc_pre_time * self.sample_const
                last_buf = last_buf[idx:]

    def upload_fingerprint(self, fingerprint):
        acr_id = self.channel["acr_id"]
        sign = (acr_id + (32 - len(acr_id)) * chr(0)).encode()
        body = sign + fingerprint
        header = struct.pack("!cBBBIB", "M", 1, 24, 1, len(body) + 1, 1)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.upload_timeout)
        s.connect((self.channel["host"], self.channel["port"]))
        s.send(header + body)

        row = struct.unpack("!ii", s.recv(8))
        msg = s.recv(row[1])
        logger.info(f"stream={self.stream.uuid}, {len(fingerprint)}, msg={msg}")


class LiveStreamWorker:
    def __init__(self, stream, channel):
        queue = Queue()
        self.decode_worker = DecodeWorker(stream, channel, queue)
        self.fingerprint_worker = FingerprintWorker(stream, channel, queue)

    def start(self):
        self.decode_worker.start()
        self.fingerprint_worker.start()

    def join(self):
        self.decode_worker.join()
        self.fingerprint_worker.join()


class LiveStreamManagerProcess(Process):
    def __init__(self, streams_channels):
        super().__init__()
        self.daemon = True
        self.workers = []
        self.streams_channels = streams_channels

    def run(self):
        for stream, channel in self.streams_channels.items():
            worker = LiveStreamWorker(stream, channel)
            worker.start()
            self.workers.append(worker)

        while self.workers:
            for worker in self.workers:
                worker.join()


class Command(BaseCommand):

    help = "Stream to ACRCloud"

    def handle(self, *args, **kwargs):
        streams = Stream.objects.live().filter(acrcloud_acr_id__isnull=False)
        streams_channels = {
            stream: acrcloud.get_channel(stream.acrcloud_acr_id) for stream in streams
        }
        LiveStreamManagerProcess(streams_channels)
