import socket
import ssl

# TODO: htmlsoup

USER_AGENT = "Memex"


class URL:
    def __init__(self, url):
        if url.startswith("data"):
            self.scheme, url = url.split(":", 1)
            self.mime, url = url.split(",", 1)
            self.dataContent = url
            return
        else:
            self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file", "data", "view-source:http"]
        if self.scheme in ["http", "view-source:http"]:
            self.port = 80
        elif self.scheme in ["https", "view-source:https"]:
            self.port = 443

        if "/" not in url:
            url += "/"

        self.host, url = url.split("/", 1)

        if hasattr(self, "host") and ":" in self.host:
            self.host, port = self.host.split(":", 1)
            # TODO: reassigning port, check for conflicts with http/s, where self.port would be 80/443 and not the custom port e.g 8080, 3000 etc.
            self.port = int(port)

        self.path = "/" + url

    def request(self):
        def createRequest():
            # Create Request and its Header
            request = f"""GET {self.path} HTTP/1.1\r
Host: {self.host}\r
Connection: Keep-Alive\r
User-Agent: {USER_AGENT}\r
"""  # Requests must end in a line break.

            request += "\r\n"

            return request

        def getResponseHeaders(response):
            response_headers = {}
            while True:
                line = response.readline()
                if line == "\r\n":
                    break
                header, value = line.split(":", 1)
                response_headers[header.casefold()] = value.strip()

            return response_headers

        if self.scheme == "data":
            return self.dataContent
        elif self.scheme == "file":
            return open((self.host + self.path).rstrip("/"), "r")

        if not hasattr(self, "savedSocket"):
            if self.scheme == "data":
                return self.dataContent

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
        else:
            s = self.savedSocket

        # Establish Connection
        try:
            s.connect((self.host, self.port))
        except socket.error as exc:
            print("Caught exception socket.error : %s" % exc.errno)

        request = createRequest()

        # Send Request
        s.send(request.encode("utf8"))

        # Handle Response
        response = s.makefile("r", encoding="utf8", newline="\r\n")

        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        if self.scheme == "view-source:http":
            return response

        response_headers = getResponseHeaders(response)

        print(response_headers)

        # Check if out data is being sent in an unusual way.
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        # Save content
        content = response.read(int(response_headers["content-length"]))

        # Save Socket
        self.savedSocket = s

        return content


def show(body):
    in_tag = False
    entity_counter = []
    for char in body:
        if char == "<":
            in_tag = True
        if char == ">":
            in_tag = False
        elif not in_tag:
            if char in "&lgt;":
                entity_counter.append(char)
            else:
                for c in entity_counter:
                    print(c, end="")
                entity_counter = []

                print(char, end="")

        if "".join(entity_counter) in "&lt;" or "".join(entity_counter) in "&gt;":
            if "".join(entity_counter) == "&lt;":
                print("<", end="")
                entity_counter = []
            elif "".join(entity_counter) == "&gt;":
                print(">", end="")
                entity_counter = []

    if len(entity_counter):  # If anything remains in entity_counter
        for c in entity_counter:
            print(c, end="")


def load(url):
    content = url.request()
    show(content)


if __name__ == "__main__":
    import sys

    try:
        load(URL(sys.argv[1]))
    except Exception as e:
        show(open("/home/ram-avni/textToOpen.txt", "r"))
        print("\n\n\n\n" + e.__str__())
