import urllib.request
import urllib.parse
import gzip
import io
from flask import Flask, request, Response

app = Flask(__name__)

def fetch_url(target):
    """Забирает URL с правильными заголовками и обработкой редиректов."""
    req = urllib.request.Request(target, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': 'https://disk.yandex.ru/',
        'Connection': 'keep-alive'
    })

    # Следуем редиректам вручную (urllib теряет заголовки)
    max_redirects = 5
    for _ in range(max_redirects):
        response = urllib.request.urlopen(req, timeout=30)
        if response.status in (301, 302, 303, 307, 308):
            new_url = response.headers.get('Location')
            if not new_url:
                break
            req = urllib.request.Request(new_url, headers=req.headers)
            continue
        return response
    return response

def decompress(data, encoding):
    if encoding == 'gzip':
        return gzip.decompress(data)
    if encoding == 'deflate':
        return gzip.decompress(data)
    return data

@app.route('/')
def proxy():
    target = request.args.get('url')
    if not target:
        return Response('Need url param', status=400, headers={'Access-Control-Allow-Origin': '*'})
    
    target = urllib.parse.unquote(target)
    
    try:
        response = fetch_url(target)
        data = response.read()
        
        # Распаковываем, если сжато
        encoding = response.headers.get('Content-Encoding', '').lower()
        try:
            data = decompress(data, encoding)
        except Exception:
            pass
        
        # Определяем content-type
        content_type = response.headers.get('Content-Type', 'application/json')
        
        return Response(
            data,
            status=response.status,
            mimetype=content_type,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        )
    except urllib.error.HTTPError as e:
        return Response(
            'Upstream HTTP error: ' + str(e.code) + ' ' + e.reason,
            status=e.code,
            headers={'Access-Control-Allow-Origin': '*'}
        )
    except Exception as e:
        return Response(
            'Proxy error: ' + str(e),
            status=500,
            headers={'Access-Control-Allow-Origin': '*'}
        )

@app.route('/', methods=['OPTIONS'])
def options():
    return Response('', status=200, headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
