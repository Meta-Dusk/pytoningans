"""
PyToNingans Mod Browser - OAuth Callback Listener
=================================================
Lightweight local HTTP redirect server and request handler for handling
OAuth browser redirects (e.g. Google Sign-In via Supabase Auth).
"""
from __future__ import annotations

import http.server, threading, urllib.parse
from typing import Any, Callable


class OAuthCallbackServer(http.server.HTTPServer):
    """Local HTTP server that holds a callback for captured OAuth tokens."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[http.server.BaseHTTPRequestHandler],
        token_callback: Callable[[str, str], None],
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.token_callback: Callable[[str, str], None] = token_callback


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """
    Handles local HTTP callbacks from the web browser during OAuth authorization.
    Serves a client-side bridge for hash fragments, extracts query parameters,
    and returns a success confirmation page.
    """

    def do_GET(self) -> None:
        parsed: urllib.parse.ParseResult = urllib.parse.urlparse(self.path)

        if parsed.path == "/callback":
            # Serve intermediate bridging HTML that captures hash fragments and passes them to /token
            html: str = (
                "<!DOCTYPE html><html><head><title>PyToNingans Auth</title></head>"
                "<body style='font-family:sans-serif;text-align:center;padding:50px;"
                "background:#181825;color:#cdd6f4;'>"
                "<h2>Connecting to PyToNingans...</h2>"
                "<p>Finalizing your sign in, please wait a moment.</p>"
                "<script>"
                "if(window.location.hash){"
                "  window.location.href='/token?' + window.location.hash.substring(1);"
                "} else if(window.location.search){"
                "  window.location.href='/token' + window.location.search;"
                "}"
                "</script></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif parsed.path == "/token":
            query_params: dict[str, list[str]] = urllib.parse.parse_qs(parsed.query)
            access_token: str = query_params.get("access_token", [""])[0]
            refresh_token: str = query_params.get("refresh_token", [""])[0]

            success_html: str = (
                "<!DOCTYPE html><html><head><title>Sign In Successful</title></head>"
                "<body style='font-family:sans-serif;text-align:center;padding:60px;"
                "background:#181825;color:#a6e3a1;'>"
                "<h1>Authentication Successful!</h1>"
                "<p style='color:#cdd6f4;'>You are now logged into PyToNingans.</p>"
                "<p style='color:#a6adc8;'>You can safely close this browser window and return to the app.</p>"
                "</body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(success_html.encode("utf-8"))

            if access_token and isinstance(self.server, OAuthCallbackServer):
                threading.Thread(
                    target=self.server.token_callback,
                    args=(access_token, refresh_token),
                    daemon=True,
                ).start()

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy HTTP stdout logging
        pass
