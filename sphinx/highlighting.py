"""
    sphinx.highlighting
    ~~~~~~~~~~~~~~~~~~~

    Highlight code blocks using Pygments.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import html
import warnings

from pygments import highlight
from pygments.filters import ErrorToken
from pygments.formatters import HtmlFormatter, LatexFormatter
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.lexers import PythonLexer, Python3Lexer, PythonConsoleLexer, \
    CLexer, TextLexer, RstLexer
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound

from sphinx.deprecation import RemovedInSphinx30Warning
from sphinx.ext import doctest
from sphinx.locale import __
from sphinx.pygments_styles import SphinxStyle, NoneStyle
from sphinx.util import logging
from sphinx.util.texescape import tex_hl_escape_map_new

if False:
    # For type annotation
    from typing import Any, Dict  # NOQA
    from pygments.formatter import Formatter  # NOQA
    from pygments.style import Style  # NOQA


logger = logging.getLogger(__name__)

lexers = {
    'none': TextLexer(stripnl=False),
    'python': PythonLexer(stripnl=False),
    'python3': Python3Lexer(stripnl=False),
    'pycon': PythonConsoleLexer(stripnl=False),
    'pycon3': PythonConsoleLexer(python3=True, stripnl=False),
    'rest': RstLexer(stripnl=False),
    'c': CLexer(stripnl=False),
}  # type: Dict[str, Lexer]
for _lexer in lexers.values():
    _lexer.add_filter('raiseonerror')


escape_hl_chars = {ord('\\'): '\\PYGZbs{}',
                   ord('{'): '\\PYGZob{}',
                   ord('}'): '\\PYGZcb{}'}

# used if Pygments is available
# use textcomp quote to get a true single quote
_LATEX_ADD_STYLES = r'''
\renewcommand\PYGZsq{\textquotesingle}
'''


class PygmentsBridge:
    # Set these attributes if you want to have different Pygments formatters
    # than the default ones.
    html_formatter = HtmlFormatter
    latex_formatter = LatexFormatter

    def __init__(self, dest='html', stylename='sphinx', trim_doctest_flags=None):
        # type: (str, str, bool) -> None
        self.dest = dest

        style = self.get_style(stylename)
        self.formatter_args = {'style': style}  # type: Dict[str, Any]
        if dest == 'html':
            self.formatter = self.html_formatter
        else:
            self.formatter = self.latex_formatter
            self.formatter_args['commandprefix'] = 'PYG'

        self.trim_doctest_flags = trim_doctest_flags
        if trim_doctest_flags is not None:
            warnings.warn('trim_doctest_flags option for PygmentsBridge is now deprecated.',
                          RemovedInSphinx30Warning, stacklevel=2)

    def get_style(self, stylename):
        # type: (str) -> Style
        if stylename is None or stylename == 'sphinx':
            return SphinxStyle
        elif stylename == 'none':
            return NoneStyle
        elif '.' in stylename:
            module, stylename = stylename.rsplit('.', 1)
            return getattr(__import__(module, None, None, ['__name__']), stylename)
        else:
            return get_style_by_name(stylename)

    def get_formatter(self, **kwargs):
        # type: (Any) -> Formatter
        kwargs.update(self.formatter_args)
        return self.formatter(**kwargs)

    def unhighlighted(self, source):
        # type: (str) -> str
        warnings.warn('PygmentsBridge.unhighlighted() is now deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        if self.dest == 'html':
            return '<pre>' + html.escape(source) + '</pre>\n'
        else:
            # first, escape highlighting characters like Pygments does
            source = source.translate(escape_hl_chars)
            # then, escape all characters nonrepresentable in LaTeX
            source = source.translate(tex_hl_escape_map_new)
            return '\\begin{Verbatim}[commandchars=\\\\\\{\\}]\n' + \
                   source + '\\end{Verbatim}\n'

    def get_lexer(self, source, lang, opts=None, location=None):
        # type: (str, str, Any, Any) -> Lexer
        # find out which lexer to use
        if lang in ('py', 'python'):
            if source.startswith('>>>'):
                # interactive session
                lexer = lexers['pycon']
            else:
                lexer = lexers['python']
        elif lang in ('py3', 'python3', 'default'):
            if source.startswith('>>>'):
                lexer = lexers['pycon3']
            else:
                lexer = lexers['python3']
        elif lang == 'guess':
            try:
                lexer = guess_lexer(source)
            except Exception:
                lexer = lexers['none']
        else:
            if lang in lexers:
                lexer = lexers[lang]
            else:
                try:
                    lexer = lexers[lang] = get_lexer_by_name(lang, **(opts or {}))
                except ClassNotFound:
                    logger.warning(__('Pygments lexer name %r is not known'), lang,
                                   location=location)
                    lexer = lexers['none']
                else:
                    lexer.add_filter('raiseonerror')

        return lexer

    def highlight_block(self, source, lang, opts=None, location=None, force=False, **kwargs):
        # type: (str, str, Any, Any, bool, Any) -> str
        if not isinstance(source, str):
            source = source.decode()

        lexer = self.get_lexer(source, lang, opts, location)

        # trim doctest options if wanted
        if isinstance(lexer, PythonConsoleLexer) and self.trim_doctest_flags:
            source = doctest.blankline_re.sub('', source)
            source = doctest.doctestopt_re.sub('', source)

        # highlight via Pygments
        formatter = self.get_formatter(**kwargs)
        try:
            hlsource = highlight(source, lexer, formatter)
        except ErrorToken:
            # this is most probably not the selected language,
            # so let it pass unhighlighted
            if lang == 'default':
                pass  # automatic highlighting failed.
            else:
                logger.warning(__('Could not lex literal_block as "%s". '
                                  'Highlighting skipped.'), lang,
                               type='misc', subtype='highlighting_failure',
                               location=location)
            hlsource = highlight(source, lexers['none'], formatter)

        if self.dest == 'html':
            return hlsource
        else:
            return hlsource.translate(tex_hl_escape_map_new)

    def get_stylesheet(self):
        # type: () -> str
        formatter = self.get_formatter()
        if self.dest == 'html':
            return formatter.get_style_defs('.highlight')
        else:
            return formatter.get_style_defs() + _LATEX_ADD_STYLES
