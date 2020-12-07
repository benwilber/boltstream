#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: qinxue.pan 
# Email : xue@arcloud.com
# Date  : 2016/08/15

import os, sys
import json, Queue, struct, urllib, urllib2, logging
import re
import threading
import hashlib
import urlparse
import time
import base64
import socket
import hmac
import subprocess
import multiprocessing
from xml.dom import minidom
import acrcloud_stream_decode

reload(sys)
sys.setdefaultencoding("utf8")

class LiveStreamWorker():

    def __init__(self, stream_info, config):
        self._stream_info = stream_info
        self._config = config
        self._logger = logging.getLogger('acrcloud_stream')
        
    def start(self):
        try:
            work_queue = Queue.Queue()
            decode_worker = self._DecodeStreamWorker(work_queue, self._stream_info, self._config)
            self._decode_worker = decode_worker
            decode_worker.start()
            process_worker = self._ProcessFingerprintWorker(work_queue, self._stream_info, self._config)
            self._process_worker = process_worker
            process_worker.start()
        except Exception as e:
            self._logger.error(str(e))

    def wait(self):
        try:
            self._decode_worker.join()
            self._process_worker.join()
        except Exception as e:
            self._logger.error(str(e))

    class _DecodeStreamWorker(threading.Thread):

        def __init__(self, worker_queue, stream_info, config):
            threading.Thread.__init__(self)
            self.setDaemon(True)
            self._config = config
            self._stream_url = stream_info['url']
            self._stream_url_list = []
            self._stream_acrid = stream_info['acr_id']
            self._program_id = stream_info.get('program_id', -1)
            self._worker_queue = worker_queue
            self._fp_interval = self._config.get('fp_interval_sec', 2)
            self._download_timeout = self._config.get('download_timeout_sec', 10)
            self._is_stop = True
            self._logger = logging.getLogger('acrcloud_stream')

        def run(self):
            self._is_stop = False
            self._logger.info(self._stream_acrid + " DecodeStreamWorker running!")
            self._check_url()
            self._logger.info(self._stream_url + ", after check_url:" + str(self._stream_url_list))
            while not self._is_stop:
                try:
                    for stream_url in self._stream_url_list:
                        self._decode_stream(stream_url)
                        time.sleep(1)
                except Exception as e:
                    self._logger.error(str(e))
            self._logger.info(self._stream_acrid + " DecodeStreamWorker stopped!")

        def _decode_stream(self, stream_url):
            try:
                acrdict = {
                    'callback_func': self._decode_callback,
                    'stream_url': stream_url,
                    'read_size_sec':self._fp_interval,
                    'program_id':self._program_id,
                    'open_timeout_sec':self._download_timeout,
                    'read_timeout_sec':self._download_timeout,
                    'is_debug':0,
                }
                code, msg = acrcloud_stream_decode.decode_audio(acrdict)
                if code == 0:
                    self._is_stop = True
                else:
                    self._logger.error("CODE:"+str(code) + ", MSG:"+str(msg))
            except Exception as e:
                self._logger.error(str(e))

        def _decode_callback(self, isvideo, buf):
            try:
                if self._is_stop:
                    return 1
                self._worker_queue.put(buf)
                return 0
            except Exception as e:
                self._logger.error(str(e))
        
        def _check_url(self):
            try:
                if self._stream_url.strip().startswith("mms://"):
                    slist = self._parse_mms(self._stream_url)
                    if slist:
                        self._stream_url_list = slist
                        return
                
                path = urlparse.urlparse(self._stream_url).path
                ext = os.path.splitext(path)[1]
                if ext == '.m3u':
                    slist = self._parse_m3u(self._stream_url)
                    if slist:
                        self._stream_url_list = slist
                elif ext == '.xspf':
                    slist = self._parse_xspf(self._stream_url)
                    if slist:
                        self._stream_url_list = slist
                elif ext == '.pls':
                    slist = self._parse_pls(self._stream_url)
                    if slist:
                        self._stream_url_list = slist
                else:
                    self._stream_url_list = [self._stream_url]
            except Exception as e:
                self._logger.error(str(e))

        def _parse_pls(self, url):
            plslist = []
            pageinfo = self._get_page(url)
            plslist = re.findall(r'(http.*[^\r\n\t ])', pageinfo)
            return plslist
            
        def _parse_m3u(self, url):
            m3ulist = []
            pageinfo = self._get_page(url)
            m3ulist = re.findall(r'(http.*[^\r\n\t "])', pageinfo)
            return m3ulist

        def _parse_xspf(self, url):
            #introduce: http://www.xspf.org/quickstart/
            xspflist = []
            pageinfo = self._get_page(url)
            xmldoc = minidom.parseString(pageinfo)
            tracklist = xmldoc.getElementsByTagName("track")
            for track in tracklist:
                loc = track.getElementsByTagName('location')[0]
                xspflist.append(loc.childNodes[0].data)
            return xspflist

        def _parse_mms(self, url):
            mmslist = []
            convert = ['mmsh', 'mmst', 'rtsp']
            mmslist = [ conv + url[3:] for conv in convert ]
            return mmslist

        def _get_page(self, url):
            resp = ''
            for i in range(2):
                req = urllib2.Request(url)
                try:
                    if url.startswith("https"):
                        context = ssl._create_unverified_context()
                        resp = urllib2.urlopen(req, context=context)
                    else:
                        resp = urllib2.urlopen(req)

                    if resp:
                        result = resp.read()
                        resp.close()
                        return result
                except Exception, e:
                    self._logger.error(str(e))
                    if resp:
                        resp.close()
            return ''
        
    class _ProcessFingerprintWorker(threading.Thread):

        def __init__(self, worker_queue, stream_info, config):
            threading.Thread.__init__(self)
            self.setDaemon(True)
            self._config = config
            self._worker_queue = worker_queue
            self._stream_info = stream_info
            self._fp_time = self._config.get('fp_time_sec', 6)
            self._fp_max_time = self._config.get('fp_max_time_sec', 12)
            self._fp_interval = self._config.get('fp_interval_sec', 2)
            self._upload_timeout = self._config.get('upload_timeout_sec', 10)
            self._record_upload_interval = self._config.get('record_upload_interval', 60)
            self._record_fp_max_time = self._config.get('record_fp_max_time', 120)
            self._record_upload = self._config.get('record_upload', 0)
            self._is_stop = True
            self._logger = logging.getLogger('acrcloud_stream')

        def run(self):
            last_buf = ''
            record_last_buf = ''
            doc_pre_time = self._fp_time - self._fp_interval
            acr_id = self._stream_info['acr_id']
            self._logger.info(acr_id + " ProcessFingerprintWorker running!")
            self._is_stop = False
            timeshift = self._stream_info.get('timeshift', 0);
            while not self._is_stop:
                try:
                    live_upload = True
                    now_buf = self._worker_queue.get()
                    cur_buf = last_buf + now_buf
                    last_buf = cur_buf

                    fp = acrcloud_stream_decode.create_fingerprint(cur_buf, False)
                    if fp and not self._upload(fp):
                        live_upload = False
                        if len(last_buf) > self._fp_max_time*16000:
                            last_buf = last_buf[len(last_buf)-self._fp_max_time*16000:]

                    if live_upload and len(last_buf) > doc_pre_time*16000:
                        last_buf = last_buf[-1*doc_pre_time*16000:]

                    if self._record_upload == 1 or timeshift:
                        record_last_buf = record_last_buf + now_buf
                        if len(record_last_buf) > self._record_upload_interval * 16000:
                            record_fp = acrcloud_stream_decode.create_fingerprint(record_last_buf, False)
                            if record_fp and self._upload_record(record_fp):
                                record_last_buf = ''
                            else:
                                if len(record_last_buf) > self._record_fp_max_time * 16000:
                                    record_last_buf = record_last_buf[len(last_buf)-self._record_fp_max_time*16000:]

                except Exception as e:
                    self._logger.error(str(e))
            self._logger.info(acr_id + " ProcessFingerprintWorker stopped!")

        def _upload(self, fp):
            result = True
            acr_id = self._stream_info['acr_id']
            try:
                host = self._stream_info['host']
                port = self._stream_info['port']
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self._upload_timeout)
                sign = acr_id + (32-len(acr_id))*chr(0)
                body = str(sign) + fp
                header = struct.pack('!cBBBIB', 'M', 1, 24, 1, len(body)+1, 1)
                sock.connect((host, port))
                sock.send(header+body)
                row = struct.unpack('!ii', sock.recv(8))
                self._logger.info(acr_id + ":" + str(len(fp)) + ":" + sock.recv(row[1]))
                sock.close()
            except Exception as e:
                result = False
                self._logger.error(acr_id + ":" + str(len(fp)) + ":" + str(e))

            return result
        def _upload_record(self, fp):
            result = True
            acr_id = self._stream_info['acr_id']
            stream_id = self._stream_info['id']
            timestamp = int(time.time())
            detail = str(stream_id)+":"+str(timestamp)
            try:
                host = self._stream_info['record_host']
                port = self._stream_info['record_port']
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self._upload_timeout)
                sign = acr_id + (32-len(acr_id))*chr(0)
                body = str(sign) +struct.pack('I', len(detail)) + detail + fp
                header = struct.pack('!cBBBIB', 'M', 1, 24, 0, len(body)+1, 2)
                sock.connect((host, port))
                sock.send(header+body)
                row = struct.unpack('!ii', sock.recv(8))
                self._logger.info(acr_id + ":record:" + str(len(fp)) + ":" + detail+":"+ sock.recv(row[1]))
                sock.close()
            except Exception as e:
                result = False
                self._logger.error(acr_id + ":record:" + str(len(fp)) + ":" + str(e))

            return result

class LiveStreamManagerProcess(multiprocessing.Process):

    def __init__(self, streams, config):
        multiprocessing.Process.__init__(self)
        self.daemon = True
        self._streams = streams
        self._config = config
        self._workers = []

    def run(self):
        if self._config.get('debug'):
            init_log(logging.INFO, self._config['log_file'])
        else:
            init_log(logging.ERROR, self._config['log_file'])
        self.run_worker()
        self.wait()

    def run_worker(self):
        try:
            for stream_t in self._streams:
                worker = LiveStreamWorker(stream_t, self._config)
                worker.start()
                self._workers.append(worker)
        except Exception as e:
            self._logger.error(str(e))

    def wait(self):
        try:
            for w in self._workers:
                w.wait()
        except Exception as e:
            self._logger.error(str(e))

class LiveStreamClient():

    def __init__(self, config):
        self._is_stop = True
        self._manager_process = []
        self._config = config
        self._logger = logging.getLogger('acrcloud_stream')

    def start_single(self):
        self._run_single()

    def start_withwatch(self):
        client_process = self._run_by_process()
        restart_interval = int(self._config.get('restart_interval_minute', 0)) * 60

        watch_num = 0
        self._is_stop = False
        while not self._is_stop:
            if not self._check_alive():
                self._kill_process()
                self._run_by_process()
                watch_num = 0
            time.sleep(1)
            watch_num = watch_num + 1
            if restart_interval > 0 and watch_num >= restart_interval:
                self._kill_process()
                self._run_by_process()
                watch_num = 0

    def _run_single(self):
        client_process = LiveStreamManagerProcess(self._config['streams'], self._config)
        client_process.run_worker()
        self._manager_process.append(client_process)
        for mp in self._manager_process:
            mp.wait()
                 
    def _run_by_process(self):
        self._manager_process = []
        try:
            client_process = LiveStreamManagerProcess(self._config['streams'], self._config)
            client_process.start()
            self._manager_process.append(client_process)
        except Exception as e:
            self._logger.error(str(e))

    def _check_alive(self):
        res = True
        try:
            for mp in self._manager_process:
                if not mp.is_alive():
                    res = False
                    break
        except Exception, e:
            self._logger.error(str(e))
        return res


    def _kill_process(self):
        try:
            for mp in self._manager_process:
                mp.terminate()
                mp.join()
        except Exception, e:
            self._logger.error(str(e))

def get_remote_config(config):
    try:

        bucket_name = config['bucket_name']
        account_access_key = config['access_key']
        account_access_secret = config['access_secret']
        requrl = "https://api.acrcloud.com/v1/buckets/"+bucket_name+"/channels"
        http_method = "GET"
        http_uri = "/v1/buckets/"+bucket_name+"/channels"
        signature_version = "1" 
        timestamp = time.time()

        string_to_sign = http_method+"\n"+http_uri+"\n"+account_access_key+"\n"+signature_version+"\n"+str(timestamp)
        sign = base64.b64encode(
                        hmac.new(account_access_secret, string_to_sign, digestmod=hashlib.sha1)
                                .digest())

        headers = {'access-key': account_access_key, 'signature-version': signature_version, 'signature': sign, 'timestamp':str(timestamp)}

        req = urllib2.Request(requrl, headers=headers)
        response = urllib2.urlopen(req)
        recv_msg = response.read()
        json_res = json.loads(recv_msg)
        config['streams'] = json_res['items']
        logging.getLogger('acrcloud_stream').info(recv_msg)

    except Exception, e:
        logging.getLogger('acrcloud_stream').error('get_remote_config : %s' % str(e))
        sys.exit(-1)


def init_log(logging_level, log_file):
    try:
        logger1 = logging.getLogger('acrcloud_stream')
        logger1.setLevel(logging_level)
        if log_file.strip():
            acrcloud_stream = logging.FileHandler(log_file)
            acrcloud_stream.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'))
            acrcloud_stream.setLevel(logging_level)
            logger1.addHandler(acrcloud_stream)
        else:
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'))
            ch.setLevel(logging_level)
            logger1.addHandler(ch)
        return logger1
    except Exception, e:
        print str(e)
        sys.exit(-1)

def parse_config():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        confpath = sys.argv[1]
    else:
        confpath = './client.conf'

    config = {}
    try:
        init_config = {}
        execfile(confpath, init_config)
        log_file = init_config.get('log_file', '')
        config['log_file'] = log_file
        config['debug'] = init_config.get('debug')
        if init_config.get('debug'):
            init_log(logging.INFO, log_file)
        else:
            init_log(logging.ERROR, log_file)

        config['access_key'] = init_config['console_access_key']
        config['access_secret'] = init_config['console_access_secret']
        config['remote'] = init_config.get('remote')
        config['restart_interval_minute'] = init_config.get('restart_interval_minute', 0)
        config['is_run_with_watchdog'] = init_config.get('is_run_with_watchdog', 0)
        config['upload_timeout_sec'] = init_config.get('upload_timeout_sec', 10)
        config['bucket_name'] = init_config.get('bucket_name')
        config['record_upload'] = init_config.get('record_upload')
        config['record_upload_interval'] = init_config.get('record_upload_interval')
        if init_config.get('remote'):
            get_remote_config(config)
        else:
            config['streams'] = []
            for stream_t in init_config['source']:
                tmp_stream_info = {'url':stream_t[0], 'acr_id':stream_t[1]}
                if len(stream_t) == 3:
                    tmp_stream_info['program_id'] = int(stream_t[2])
                tmp_stream_info['host'] = init_config['server']['host']
                tmp_stream_info['port'] = init_config['server']['port']
                config['streams'].append(tmp_stream_info)
    except Exception, e:
        print "Error: Load ./client.conf failed." + str(e)
        sys.exit(1)
    return config


def main():
    config = parse_config()
    client = LiveStreamClient(config)
    if config.get("is_run_with_watchdog"):
        client.start_withwatch()
    else:
        client.start_single()

if __name__ == '__main__':
    main()
