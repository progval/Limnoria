try:
    from importlib.metadata import get_distribution
except ImportError:
    # Python < 3.7
    from pkg_resources import get_distribution

import supybot.utils.python

version = get_distribution("limnoria").version
supybot.utils.python._debug_software_version = version
