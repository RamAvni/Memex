import socket


class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme == "http"
        if "/" not in url:
            url += "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url

    def request(self):
        # Create socket
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        # Establish Connection
        s.connect((self.host, 80))

        # Create Request
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
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
