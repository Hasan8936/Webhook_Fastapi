from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

http_requests_total = Counter("http_requests_total", "HTTP requests total", ["path", "status"]) 
webhook_requests_total = Counter("webhook_requests_total", "Webhook requests total", ["result"]) 
request_latency_seconds = Histogram("request_latency_seconds", "Request latency seconds")


def metrics_endpoint():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
