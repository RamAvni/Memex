import socket
import ssl
import os

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

    def request(self, HttpMethod):
        def createRequest():
            # Create Request and its Header
            request = f"""{HttpMethod} {self.path} HTTP/1.1\r
Host: {self.host}\r
Connection: Keep-Alive\r
User-Agent: {USER_AGENT}\r
Accept-Encoding: gzip\r
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

        def cache(fileName, extension, content):
            hostDirectoryCachePath = f"localCache/{self.host}"
            newFilePath = f"{hostDirectoryCachePath}/{fileName}.{extension}"

            # Create host's cache directory if it doesn't exist
            if not os.path.isdir(hostDirectoryCachePath):
                os.mkdir(hostDirectoryCachePath)

            newFile = open(newFilePath, "w")
            newFile.write(content)
            newFile.close()

        if self.scheme == "data":
            return self.dataContent
        elif self.scheme == "file":
            return open((self.host + self.path).rstrip("/"), "r")

        if not hasattr(self, "savedSocket"):
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
        # Handle redirects
        if 300 <= int(status) < 400 and response_headers["location"]:
            location = response_headers["location"]
            if location.startswith("/"):
                redirectURL = URL(f"{self.scheme}://{self.host}{location}")
            else:
                redirectURL = URL(location)
            return redirectURL.request(HttpMethod)

        # Check if out data is being sent in an unusual way.
        assert (
            "transfer-encoding" not in response_headers
        ), "transfer-encoding is in response_headers"
        assert (
            "content-encoding" not in response_headers
        ), "content-encoding is in response_headers"
        if "cache-control" in response_headers:
            assert response_headers["cache-control"] in [
                "no-store",
                "max-age",
            ], f"Unsupported cache-control: {response_headers['cache-control']}"

        # Get content
        if os.path.isfile(
            f"localCache/{self.host}/{response_headers['etag'][1:-1]}.{response_headers["content-type"].split("/")[1]}"
        ):
            print("Read file from cache")
            cachedFile = open(
                f"localCache/{self.host}/{response_headers['etag'][1:-1]}.{response_headers["content-type"].split("/")[1]}"
            )
            content = cachedFile.read()
            cachedFile.close()
        else:
            print("Read file from response")
            content = response.read(int(response_headers["content-length"]))[1:-1]

        # Save Socket
        self.savedSocket = s

        if (
            HttpMethod == "GET"
            and int(status) == 200
            and "cache-control" in response_headers
        ):
            cache(
                response_headers["etag"][1:-1],
                response_headers["content-type"].split("/")[1],
                content,
            )
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
    content = url.request("GET")
    show(content)


if __name__ == "__main__":
    import sys

    try:
        load(URL(sys.argv[1]))
    except Exception as e:
        show(open("/home/ram-avni/textToOpen.txt", "r"))
        print("\n\n\n\nError:")
        print(e)


# * 1. Your browser must send the Accept-Encoding header with the value gzip.
# * 2. If the server supports compression, its response will have a Content-Encoding header with value gzip. The body is then compressed. Add support for this case. - print the compressed response, see you got it.
# * 3. To decompress the data, you can use the decompress method in the gzip module. GZip data is not utf8-encoded, so pass "rb" to makefile to work with raw bytes instead.
# * 4. Most web servers send compressed data in a Transfer-Encoding called chunked.
