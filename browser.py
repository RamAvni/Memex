import socket
import ssl

USER_AGENT = "Memex"


class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file"]

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        if "/" not in url:
            url += "/"
        self.host, url = url.split("/", 1)
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            # TODO: reassigning port, check for conflicts with http/s, where self.port would be 80/443 and not the custom port e.g 8080, 3000 etc.
            self.port = int(port)
        self.path = "/" + url

    def request(self):
        # Create socket
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

        # Handle requests by scheme
        if self.scheme == "https":  # Create secure connection wrapper is 'https'
            context = ssl.create_default_context()
            s = context.wrap_socket(s, server_hostname=self.host)
        elif self.scheme == "file":
            return open((self.host + self.path).rstrip("/"), "r")

        # Establish Connection
        s.connect((self.host, self.port))

        # Create Request and its Header
        request = f"""GET {self.path} HTTP/1.1\r
Host: {self.host}\r
Connection: close\r
User-Agent: {USER_AGENT}\r
"""  # Requests must end in a line break.

        print("request: ", request)
        request += "\r\n"

        # Send Request
        s.send(request.encode("utf8"))

        # Handle Response
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        # Check if out data is being sent in an unusual way.
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        # Save content
        content = response.read()

        # Close connection
        s.close()

        return content


def show(body):
    in_tag = False
    for char in body:
        if char == "<":
            in_tag = True
        if char == ">":
            in_tag = False
        elif not in_tag:
            print(char, end="")


def load(url):
    content = url.request()
    show(content)


if __name__ == "__main__":
    import sys

    load(URL(sys.argv[1]))
