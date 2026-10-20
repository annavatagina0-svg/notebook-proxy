import urllib.request
import urllib.parse
import urllib.error
import gzip
import json
import ssl
from flask import Flask, request, Response

app = Flask(__name__)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def http_get(url, headers=None, timeout=30):
    h = {
        'User-Agent': UA,
        'Accept': '*/*',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        'Connection': 'keep-alive'
    }
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout, context=ssl_context)


def decompress(data, encoding):
    encoding = (encoding or '').lower()
    if encoding == 'gzip':
        return gzip.decompress(data)
    if encoding == 'deflate':
        try:
            return gzip.decompress(data)
        except Exception:
            import zlib
            return zlib.decompress(data)
    return data


@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@app.route('/', methods=['OPTIONS'])
def options():
    return Response('', status=200)


@app.route('/')
def proxy():
    target = request.args.get('url')
    path = request.args.get('path')
    token = request.args.get('token')

    try:
        if target:
            target = urllib.parse.unquote(target)
            response = http_get(target)
            data = response.read()
            data = decompress(data, response.headers.get('Content-Encoding', ''))
            return Response(data, status=response.status,
                            mimetype=response.headers.get('Content-Type', 'application/json'))

        if path and token:
            path = urllib.parse.unquote(path)
            api_url = 'https://cloud-api.yandex.net/v1/disk/resources/download?path=' + urllib.parse.quote(path)
            r1 = http_get(api_url, headers={'Authorization': 'OAuth ' + token})
            info = json.loads(r1.read().decode('utf-8'))
            href = info.get('href')
            if not href:
                return Response('No href: ' + json.dumps(info), status=500)
            r2 = http_get(href)
            data = r2.read()
            data = decompress(data, r2.headers.get('Content-Encoding', ''))
            return Response(data, status=200, mimetype='application/json')

        return Response('Need url or (path + token) param', status=400)

    except urllib.error.HTTPError as e:
        body = b''
        try:
            body = e.read()
        except Exception:
            pass
        msg = 'Upstream error ' + str(e.code) + ' — ' + body.decode('utf-8', errors='replace')[:300]
        return Response(msg, status=e.code)
    except Exception as e:
        return Response('Proxy error: ' + str(e), status=500)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
