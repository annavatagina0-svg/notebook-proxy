import os
import urllib.request
import urllib.parse
from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/')
def proxy():
    target = request.args.get('url')
    if not target:
        return Response('Need url param', status=400)
    
    target = urllib.parse.unquote(target)
    
    try:
        req = urllib.request.Request(target, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=25) as response:
            data = response.read()
            return Response(data, status=200, mimetype='application/json')
    except Exception as e:
        return Response('Proxy error: ' + str(e), status=500)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
