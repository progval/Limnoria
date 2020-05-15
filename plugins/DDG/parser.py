import enum
import collections
from html.parser import HTMLParser

result = collections.namedtuple('result', 'link title snippet')

@enum.unique
class ParserState(enum.Enum):
    OUTSIDE = 0
    IN_TITLE = 1
    TITLE_PARSED = 2
    IN_SNIPPET = 3

STACKED_TAGS = ('table', 'tr', 'td', 'a')

class DDGHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.results = []

        self.reset_current_result()

    def reset_current_result(self):
        self.state = ParserState.OUTSIDE
        self.current_link = None
        self.current_title = None
        self.current_snippet = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()

        if tag in STACKED_TAGS:
            self.stack.append((tag, classes))

        if ('tr', ['result-sponsored']) in self.stack:
            # Skip sponsored results
            return

        if tag == 'a' and 'result-link' in classes:
            assert self.state == ParserState.OUTSIDE, (self.state, self.current_title)
            self.state = ParserState.IN_TITLE
            self.current_link = attrs['href']
            self.current_title = []

        elif tag == 'td' and 'result-snippet' in classes:
            assert self.state == ParserState.TITLE_PARSED, self.state
            self.state = ParserState.IN_SNIPPET
            self.current_snippet = []

        elif tag == 'span' and 'link-text' in classes:
            if self.state == ParserState.TITLE_PARSED:
                # No snippet
                self.state = ParserState.OUTSIDE
                self.current_snippet = []

    def handle_endtag(self, tag):
        if tag in STACKED_TAGS:
            item = self.stack.pop()
            assert item[0] == tag, (item, tag)

        if tag == 'a' and self.state == ParserState.IN_TITLE:
            self.state = ParserState.TITLE_PARSED
        elif tag == 'td' and self.state == ParserState.IN_SNIPPET:
            self.build_result()
            self.state = ParserState.OUTSIDE

    def handle_data(self, data):
        if self.state == ParserState.IN_TITLE:
            self.current_title.append(data)
        elif self.state == ParserState.IN_SNIPPET:
            self.current_snippet.append(data)

    def build_result(self):
        self.results.append(result(
            link=self.current_link,
            title=''.join(self.current_title),
            snippet=''.join(self.current_snippet),
        ))
        self.reset_current_result()

if __name__ == '__main__':
    parser = DDGHTMLParser()
    with open('ddg2.html') as fd:
        parser.feed(fd.read())
    print(parser.results)
