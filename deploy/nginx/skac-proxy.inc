# Shared UI + API proxy. Included by the HTTP bootstrap and HTTPS server blocks.
# Do not listen/ssl here — the parent server {} owns ports and certificates.

root /opt/skac-erp/dist;
index index.html;
client_max_body_size 32m;

gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;

# Field-visit photos are multipart and can be several MB each.
location /api/ {
    proxy_pass http://127.0.0.1:5174/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 60s;
    client_max_body_size 32m;
}

location /health {
    proxy_pass http://127.0.0.1:5174/health;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /docs {
    proxy_pass http://127.0.0.1:5174/docs;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /openapi.json {
    proxy_pass http://127.0.0.1:5174/openapi.json;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location / {
    try_files $uri $uri/ /index.html;
}
