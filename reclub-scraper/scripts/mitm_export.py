"""mitmproxy addon: dump JSON flows for one host to a file for easy inspection.

Usage:
    mitmdump -s mitm_export.py --set target_host=api.reclubapp.example \
        --set out_file=captured_flows.json

Only requests/responses whose host contains `target_host` are recorded.
Bodies are only kept when the content-type looks like JSON, since that's
what you're looking for when reverse-engineering an API.
"""
import json

from mitmproxy import ctx, http

captured = []


def load(loader):
    loader.add_option("target_host", str, "", "Substring of the host to capture")
    loader.add_option("out_file", str, "captured_flows.json", "Where to write captured flows")


def _json_body(message):
    content_type = message.headers.get("content-type", "")
    if "json" not in content_type.lower():
        return None
    try:
        return json.loads(message.get_text())
    except Exception:
        return None


def response(flow: http.HTTPFlow) -> None:
    target = ctx.options.target_host
    if target and target not in flow.request.pretty_host:
        return

    captured.append(
        {
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "request_headers": dict(flow.request.headers),
            "request_json": _json_body(flow.request),
            "status_code": flow.response.status_code if flow.response else None,
            "response_json": _json_body(flow.response) if flow.response else None,
        }
    )

    with open(ctx.options.out_file, "w") as f:
        json.dump(captured, f, indent=2)

    ctx.log.info(f"Captured {flow.request.method} {flow.request.pretty_url}")
