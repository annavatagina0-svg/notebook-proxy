import urllib.request
import urllib.parse
import urllib.error
import gzip
import ssl
from flask import Flask, request, Response

app = Flask(__name__)

# Отключаем проверку SSL — иногда мешает при редиректах
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


def fetch_url(target):
    """Забирает URL с браузерными заголовками и обходом редиректов."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        'Referer': 'https://disk.yandex.ru/',
        'Connection': 'keep-alive'
    }

    current_url = target
    for _ in range(5):
        req = urllib.request.Request(current_url, headers=headers)
        # Не декодируем gzip автоматически — сделаем сами
        response = urllib.request.urlopen(req, timeout=30, context=ssl_context)
        if response.status in (301, 302, 303, 307, 308):
            location = response.headers.get('Location')
            if not location:
                return response
            current_url = location
            continue
        return response
    return response


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
    """Добавляем CORS-заголовки ко ВСЕМ ответам, включая ошибки."""
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
    if not target:
        return Response('Need url param', status=400)

    target = urllib.parse.unquote(target)

    try:
        response = fetch_url(target)
        data = response.read()

        # Распаковываем если сжато
        encoding = response.headers.get('Content-Encoding', '')
        try:
            data = decompress(data, encoding)
        except Exception:
            pass

        content_type = response.headers.get('Content-Type', 'application/json')
        return Response(data, status=response.status, mimetype=content_type)

    except urllib.error.HTTPError as e:
        return Response(
            'Upstream HTTP error: ' + str(e.code) + ' ' + str(e.reason),
            status=e.code
        )
    except urllib.error.URLError as e:
        return Response('URL error: ' + str(e.reason), status=502)
    except Exception as e:
        return Response('Proxy error: ' + str(e), status=500)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
