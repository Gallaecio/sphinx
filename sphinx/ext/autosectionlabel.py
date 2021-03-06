"""
    sphinx.ext.autosectionlabel
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Allow reference sections by :ref: role using its title.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from typing import cast

from docutils import nodes

from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.nodes import clean_astext

if False:
    # For type annotation
    from typing import Any, Dict  # NOQA
    from sphinx.application import Sphinx  # NOQA


logger = logging.getLogger(__name__)


def get_node_depth(node):
    i = 0
    cur_node = node
    while cur_node.parent != node.document:
        cur_node = cur_node.parent
        i += 1
    return i


def register_sections_as_label(app, document):
    # type: (Sphinx, nodes.Node) -> None
    labels = app.env.domaindata['std']['labels']
    anonlabels = app.env.domaindata['std']['anonlabels']
    for node in document.traverse(nodes.section):
        if (app.config.autosectionlabel_maxdepth and
                get_node_depth(node) >= app.config.autosectionlabel_maxdepth):
            continue
        labelid = node['ids'][0]
        docname = app.env.docname
        title = cast(nodes.title, node[0])
        ref_name = getattr(title, 'rawsource', title.astext())
        if app.config.autosectionlabel_prefix_document:
            name = nodes.fully_normalize_name(docname + ':' + ref_name)
        else:
            name = nodes.fully_normalize_name(ref_name)
        sectname = clean_astext(title)

        if name in labels:
            logger.warning(__('duplicate label %s, other instance in %s'),
                           name, app.env.doc2path(labels[name][0]),
                           location=node, type='autosectionlabel', subtype=docname)

        anonlabels[name] = docname, labelid
        labels[name] = docname, labelid, sectname


def setup(app):
    # type: (Sphinx) -> Dict[str, Any]
    app.add_config_value('autosectionlabel_prefix_document', False, 'env')
    app.add_config_value('autosectionlabel_maxdepth', None, 'env')
    app.connect('doctree-read', register_sections_as_label)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
