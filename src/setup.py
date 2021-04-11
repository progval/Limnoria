###
# Copyright (c) 2020, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import os
import sys

try:
    import setuptools
except ImportError:
    setuptools = None

from . import authors

if setuptools:
    def plugin_setup(plugin, **kwargs):
        """Wrapper of setuptools.setup that auto-fills some fields for
        Limnoria plugins."""
        if isinstance(plugin, str):
            if plugin in sys.modules:
                plugin = sys.modules[plugin]
            else:
                setup_path = sys.modules['__main__'].__file__
                sys.path.insert(0, os.path.join(os.path.dirname(setup_path), '..'))
                plugin = __import__(plugin)

        author = plugin.__author__
        version = plugin.__version__
        url = plugin.__url__
        maintainer = getattr(plugin, '__maintainer__', authors.unknown)

        kwargs.setdefault('package_data', {}).setdefault('', []).append('*.po')

        capitalized_name = plugin.Class.__name__
        kwargs.setdefault(
            'name', 'limnoria-%s' % capitalized_name.lower())
        if version:
            kwargs.setdefault('version', version)
        if url:
            kwargs.setdefault('url', url)

        if 'long_description' not in kwargs:
            readme_files = [
                ('text/x-rst', 'README.rst'),
                ('text/markdown', 'README.md'),
            ]
            for (mimetype, filename) in readme_files:
                readme_path = os.path.join(
                    os.path.dirname(plugin.__file__), filename)
                if os.path.isfile(readme_path):
                    with open(readme_path, 'r') as fd:
                        kwargs['long_description'] = fd.read()
                        kwargs['long_description_content_type'] = mimetype
                    break

        module_name = kwargs['name'].replace('-', '_')
        kwargs.setdefault('packages', [module_name])
        kwargs.setdefault('package_dir', {module_name: '.'})
        kwargs.setdefault('entry_points', {
            'limnoria.plugins': '%s = %s' % (capitalized_name, module_name)})

        kwargs.setdefault('install_requires', []).append('limnoria')

        kwargs.setdefault('classifiers', []).extend([
            'Environment :: Plugins',
            'Programming Language :: Python :: 3',
            'Topic :: Communications :: Chat',
        ])

        if author is not authors.unknown:
            if author.name or author.nick:
                kwargs.setdefault('author', author.name or author.nick)
            if author.email:
                kwargs.setdefault('author_email', author.email)

        if maintainer is not authors.unknown:
            if maintainer.name or maintainer.nick:
                kwargs.setdefault(
                    'maintainer', maintainer.name or maintainer.nick)
            if maintainer.email:
                kwargs.setdefault('maintainer_email', maintainer.email)

        setuptools.setup(
            **kwargs)

else:
    def plugin_setup(plugin, **kwargs):
        raise ImportError('setuptools')
