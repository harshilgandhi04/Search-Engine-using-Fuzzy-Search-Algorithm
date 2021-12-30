"""
Copyright 2019, University of Freiburg
Chair of Algorithms and Data Structures.
Hannah Bast <bast@cs.uni-freiburg.de>
Claudius Korzen <korzen@cs.uni-freiburg.de>
Patrick Brosi <brosi@cs.uni-freiburg.de>
"""
import socket
import sys
import qgram_index


class SearchServer:
    """
    Your server should behave like explained in the lecture and ES7. For a
    given URL of the form http://<host>:<port>/api?q=<query>, your server
    should return the matches for <query> as a valid JSON object.

    The web application should be dynamic, by using JavaScript and the jQuery
    library. The URL of the search page should be
    http://<host>:<port>/search.html, just like for ES6. The matches should now
    be displayed automatically after each keystroke (so that an explicit search
    button is no longer necessary), and they should be obtained via your own
    API described above. As for ES6, you should display up to 5 matches.
    """

    def __init__(self, port, ds_file_name, party_pooper):
        '''
        Inits a simple HTTP search server

        '''
        self.ds_file_name = ds_file_name
        self.port = port
        self.party_pooper = party_pooper

    def run(self):
        '''
        Start the webserver and handle requests.

        In the following, you will find some example URLs,
        each given with the expected JSON output. Note that,
        as usual, the contents of the test cases is important,
        but not the exact syntax.

        URL:
          http://<host>:<port>/api?q=angel
        RESPONSE:
          {
            "query": "angel",
            "results": [
              {
                "name": "Angela Merkel",
                "score": 180,
                "description": "Chancellor of Germany"
              },
              {
                "name": "Angelina Jolie",
                "score": 137,
                "description": "American actress, film director
                , and screenwriter"
              },
              {
                "name": "angel",
                "score": 122,
                "description": "supernatural being or spirit in
                certain religions and mythologies"
              },
              {
                "name": "Angel Falls",
                "score": 76,
                "description": "waterfall in Venezuela"
              },
              {
                "name": "Angels & Demons",
                "score": 54,
                "description": "thriller book written by Dan Brown"
              }
            ]
          }

        URL:
          http://<host>:<port>/api?q=eyj%C3%A4fja
        RESPONSE:
          {
            "query": "eyjäfja",
            "results": [
              {
                "name": "Eyjafjallajökull",
                "score": 82,
                "description": "glacier and volcano in Iceland"
              },
              {
                "name": "Eyjafjarðarsveit",
                "score": 15,
                "description": "municipality of Iceland"
              },
              {
                "name": "Eyjafjallajökull",
                "score": 7,
                "description": "2013 film by Alexandre Coffre"
              }
            ]
          }

        URL:
          http://<host>:<port>/api?q=%C3%B6ster
        RESPONSE:
          {
            "query": "öster",
            "results": [
              {
                "name": "Östersund",
                "score": 70,
                "description": "urban area in Östersund Municipality, Sweden"
              },
              {
                "name": "Östergötland County",
                "score": 59,
                "description": "county (län) in Sweden"
              },
              {
                "name": "Östergötland",
                "score": 43,
                "description": "historical province in Sweden"
              },
              {
                "name": "Österåker Municipality",
                "score": 33,
                "description": "municipality in Stockholm County, Sweden"
              },
              {
                "name": "Österreichische Bundesbahnen",
                "score": 31,
                "description": "company"
              }
            ]
          }
        '''

        # Create server socket using IPv4 addresses and TCP.
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow reuse of port if we start program again after a crash.
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Say on which machine and port we want to listen for connections.
        server_address = ("localhost", self.port)
        server_socket.bind(server_address)
        # Start listening
        server_socket.listen()

        qi = qgram_index.QGramIndex(3)
        qi.build_from_file(self.ds_file_name)

        while True:

            status_code = 200
            answer_bytes = b"Thanks for Request"
            content_type = "text/plain"
            max_num_bytes = 4096
            file_name = ""
            search_query = ""
            html_result = ""

            print("Waiting for connection on port %d ..." % self.port)

            connection, client_address = server_socket.accept()
            print("Incoming connection from ", client_address)

            request_bytes = connection.recv(max_num_bytes)
            request_str = request_bytes.decode("utf-8")

            print("Request: %s ..." % request_str.split("\r\n")[0])
            print()

            if request_str.startswith("GET"):
                file_name = request_str.split(" ")[1][1:].split("?")[0]

            if file_name != "api":
                try:
                    with open(file_name, "rb") as fl:
                        answer_bytes = fl.read()
                except Exception:
                    status_code = 404
                    answer_bytes = b"<h3>Requested file not found " \
                                   b"in server directory</h3>"

            if file_name == "api" and request_str.find("sq=") > 0:
                search_query = request_str.split("sq=")[1].split(" ")[0]
                search_query = self.url_decode(search_query)

                search_results = qi.fuzzy_search(search_query)

                html_result = "{\"query\":\"" + search_query + \
                              "\",\"results\":["
                data_lines = []
                for item in search_results:

                    if self.party_pooper:
                        name = item[0].replace(">", "&gt;") \
                            .replace("<", "&lt;")
                        description = item[2].replace(">", "&gt;") \
                            .replace("<", "&lt;")
                    else:
                        name = item[0]
                        description = item[2]

                    score = item[1]
                    wikidataurl = item[3]

                    data_lines.append(
                        "{\"name\":\"" + name +
                        "\",\"score\":\"" + score +
                        "\",\"description\":\"" + description +
                        "\",\"wikidataurl\":\"" + wikidataurl +
                        "\"}")

                html_result = html_result + ",".join(data_lines) + "]}"
                content_type = "application/json"
                answer_bytes = html_result.encode("utf-8")

            content_length = len(answer_bytes)

            if file_name.endswith(".html"):
                content_type = "text/html"
            if file_name.endswith(".css"):
                content_type = "text/css"
            if file_name.endswith(".js"):
                content_type = "application/javascript"

            headers = "HTTP/1.1 %d OK\r\n" \
                      "Content-Length: %d\r\n" \
                      "Content-Type: %s\r\n" \
                      "\r\n" % \
                      (status_code, content_length, content_type)
            connection.sendall(headers.encode("utf-8"))
            connection.sendall(answer_bytes)

            connection.close()

    def url_decode(self, str):
        '''
        Decode an URL-encoded UTF-8 string, as explained in the lecture.
        Don't forget to also decode a "+" (plus sign) to a space (" ")!

        >>> s = SearchServer(0, None, None)
        >>> s.url_decode("nirwana")
        'nirwana'
        >>> s.url_decode("the+m%C3%A4trix")
        'the mätrix'
        >>> s.url_decode("Mikr%C3%B6soft+Windos")
        'Mikrösoft Windos'
        >>> s.url_decode("The+hitschheiker%20guide")
        'The hitschheiker guide'
        '''

        search_query = str.replace("+", " ")

        i = 0
        decoded_sq = ""
        while i < len(search_query):

            if search_query[i] != "%":
                decoded_sq += search_query[i]
                i += 1
            else:
                if search_query[i + 1].isalpha():
                    hex_str = search_query[i + 1:i + 3] +\
                              search_query[i + 4:i + 6]
                    binary_str = bin(int(hex_str, 16))[2:]
                    u = "".join([chr(int(x, 2))
                                 for x in [binary_str[i:i + 8]
                                           for i in
                                           range(0, len(binary_str), 8)
                                           ]
                                 ])
                    d = u.encode("latin-1").decode('utf-8')
                    decoded_sq += d
                    i += 6
                else:
                    hex_str = search_query[i + 1:i + 3]
                    binary_str = bin(int(hex_str, 16))[2:]
                    u = "".join([chr(int(x, 2))
                                 for x in [binary_str[i:i + 8]
                                           for i in
                                           range(0, len(binary_str), 8)
                                           ]
                                 ])
                    d = u.encode("latin-1").decode('utf-8')
                    decoded_sq += d
                    i += 3
        return decoded_sq


if __name__ == "__main__":
    # Parse the command line arguments.
    if len(sys.argv) < 2:
        print("Usage: python3 %s <file> <port> "
              " [--use-synonyms] [--party-pooper]" % sys.argv[0])
        sys.exit()

    file_name = sys.argv[1]
    port = int(sys.argv[2])
    use_synonyms = "--use-synonyms" in sys.argv
    party_pooper = "--party-pooper" in sys.argv

    s = SearchServer(port, file_name, party_pooper)
    s.run()
