import os
import logging

from timeit import default_timer
from threading import Timer

import requests

import prometheus_client
from prometheus_client import Histogram, Gauge, Counter

logging.basicConfig(level='INFO', format='%(asctime)s [speedcheck] - %(message)s')
logger = logging.getLogger('speedcheck')

buckets = (.01, .05, .1, .25, .5, .75, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 30, float('inf'))

ping_histogram = Histogram('speedcheck_ping', 'Testing the ping latency', buckets=buckets)
ping_gauge = Gauge('speedcheck_ping_last', 'The last measured time of ping')

text_histogram = Histogram('speedcheck_text', 'Testing the text latency', buckets=buckets)
text_gauge = Gauge('speedcheck_text_last', 'The last measured time of text')

stream_histogram = Histogram('speedcheck_stream', 'Testing the stream latency', buckets=buckets)
stream_gauge = Gauge('speedcheck_stream_last', 'The last measured time of stream')
stream_speed = Gauge('speedcheck_stream_speed', 'The last speed of fetching the stream in bytes/sec')

http_status_count = Counter('speedcheck_http_status', 'The number of HTTP status codes seen', ('code',))
error_count = Counter('speedcheck_errors', 'Number of errors while tesing')

base_url = os.getenv('BASE_URL', 'http://localhost:5000')
metrics_port = int(os.getenv('METRICS_PORT', '3997'))


@error_count.count_exceptions()
def _execute_request(path, timeout):
    http_user = os.getenv('HTTP_USER')
    http_pass = os.getenv('HTTP_PASSWORD')

    kwargs = {}
    if http_user and http_pass:
        kwargs = {'auth': (http_user, http_pass)}

    response = requests.get('%s%s' % (base_url, path), timeout=timeout, **kwargs)
    logger.info('GET %s%s : HTTP %d' % (base_url, path, response.status_code))

    http_status_count.labels(response.status_code).inc()
    if response.status_code != 200:
        error_count.inc()

    length = 0

    for c in response.iter_content(1000):
        assert c is not None
        length += len(c)

    return length


def _safe_execute_request(path, timeout):
    try:
        return _execute_request(path, timeout)
    except:
        import traceback
        traceback.print_exc()

    return 0


@ping_gauge.time()
@ping_histogram.time()
def execute_ping():
    _safe_execute_request('/ping', timeout=10)


@text_gauge.time()
@text_histogram.time()
def fetch_text():
    _safe_execute_request('/text', timeout=15)


@stream_gauge.time()
@stream_histogram.time()
def fetch_stream():
    start = default_timer()
    length = _safe_execute_request('/stream', timeout=30)
    elapsed = default_timer() - start

    if elapsed > 0 and length > 0:
        stream_speed.set(length / elapsed)


def start_timer(name, interval, func, first_start=False):
    def _wrapper():
        func()
        start_timer(name, interval, func)

    timer = Timer(interval / 100.0 if first_start else interval, _wrapper)
    timer.setName(name)
    timer.start()


if __name__ == '__main__':
    prometheus_client.start_http_server(metrics_port, '0.0.0.0')

    start_timer('Ping', 10, execute_ping, first_start=True)
    start_timer('Text', 30, fetch_text, first_start=True)
    start_timer('Ping', 300, fetch_stream, first_start=True)  # 5 minutes
