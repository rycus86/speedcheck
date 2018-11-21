from flask import Flask, Response
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app, buckets=(.0001, .0002, .0003, .0005, .00075, .001, .005, .01, .1, 1, float('inf')))


@app.route('/ping')
def ping():
    return 'OK'


@app.route('/text')
def text():
    return 'Here is some text content, but not an awful lot. \n' * 10000  # 500 kiB


@app.route('/stream')
def stream():
    def _generate():
        with open('/dev/urandom', 'rb') as random:
            for _ in range(1024):  # 10 MB
                yield random.read(1024 * 10)

    return Response(_generate(), content_type='application/octet-stream')


if __name__ == '__main__':
    app.run('0.0.0.0', 5000, threaded=True)
