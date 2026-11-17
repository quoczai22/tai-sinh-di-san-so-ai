/**
 * Máy chủ cổng Vercel cục bộ (zero-dependency Node.js HTTP server).
 * Phục vụ cả trang tĩnh `web_ui/` lẫn các hàm serverless `web_ui/api/*.js`
 * với đúng giao diện `(req, res)` của Vercel Functions — giúp kiểm thử local
 * ngay lập tức mà không bắt buộc đăng nhập `vercel dev`.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const WEB_UI_ROOT = path.resolve(__dirname, '..', 'web_ui');
const API_DIR = path.join(WEB_UI_ROOT, 'api');
const PORT = parseInt(process.env.PORT || '3000', 10);

const MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff2': 'font/woff2',
    '.woff': 'font/woff',
};

function enhanceRes(res) {
    res.status = function status(code) {
        res.statusCode = code;
        return res;
    };
    res.json = function json(obj) {
        if (!res.getHeader('Content-Type')) {
            res.setHeader('Content-Type', 'application/json; charset=utf-8');
        }
        res.end(JSON.stringify(obj));
        return res;
    };
    res.send = function send(body) {
        if (Buffer.isBuffer(body) || typeof body === 'string') {
            res.end(body);
        } else if (body && typeof body === 'object') {
            res.json(body);
        } else {
            res.end();
        }
        return res;
    };
    return res;
}

function readRequestBody(req) {
    return new Promise((resolve, reject) => {
        const chunks = [];
        req.on('data', (chunk) => chunks.push(chunk));
        req.on('end', () => {
            const raw = Buffer.concat(chunks).toString('utf8');
            if (!raw) return resolve({});
            try {
                resolve(JSON.parse(raw));
            } catch (_) {
                resolve(raw);
            }
        });
        req.on('error', reject);
    });
}

const server = http.createServer(async (req, res) => {
    enhanceRes(res);
    const parsedUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    let pathname = parsedUrl.pathname;

    if (pathname === '/health') {
        pathname = '/api/health';
    }

    if (pathname.startsWith('/api/')) {
        const routeName = pathname.slice('/api/'.length).replace(/\/$/, '');
        if (!routeName || routeName.startsWith('_') || routeName.includes('..')) {
            return res.status(404).json({ detail: 'API route not found' });
        }
        const handlerPath = path.join(API_DIR, `${routeName}.js`);
        if (!fs.existsSync(handlerPath)) {
            return res.status(404).json({ detail: `Không tìm thấy API /api/${routeName}` });
        }
        req.query = Object.fromEntries(parsedUrl.searchParams.entries());
        if (req.method === 'POST' || req.method === 'PUT') {
            req.body = await readRequestBody(req);
        }
        try {
            const handler = require(handlerPath);
            await handler(req, res);
        } catch (err) {
            console.error(`[API Error /api/${routeName}]`, err);
            if (!res.writableEnded) {
                res.status(500).json({ detail: err.message || 'Internal Server Error' });
            }
        }
        return;
    }

    // Phục vụ file tĩnh trong web_ui/
    const relPath = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '');
    const safePath = path.resolve(WEB_UI_ROOT, relPath);
    if (!safePath.startsWith(WEB_UI_ROOT)) {
        return res.status(403).end('Forbidden');
    }

    let targetFile = safePath;
    if (fs.existsSync(targetFile) && fs.statSync(targetFile).isDirectory()) {
        targetFile = path.join(targetFile, 'index.html');
    } else if (!fs.existsSync(targetFile) && fs.existsSync(`${targetFile}.html`)) {
        targetFile = `${targetFile}.html`;
    }

    if (!fs.existsSync(targetFile) || !fs.statSync(targetFile).isFile()) {
        return res.status(404).end('Not Found');
    }

    const ext = path.extname(targetFile).toLowerCase();
    res.setHeader('Content-Type', MIME_TYPES[ext] || 'application/octet-stream');
    res.status(200).end(fs.readFileSync(targetFile));
});

server.listen(PORT, '127.0.0.1', () => {
    console.log(`Local Vercel Gateway running at http://127.0.0.1:${PORT}`);
});
