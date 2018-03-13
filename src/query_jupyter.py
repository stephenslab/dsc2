#!/usr/bin/env python
__author__ = "Gao Wang"
__copyright__ = "Copyright 2016, Stephens lab"
__email__ = "gaow@uchicago.edu"
__license__ = "MIT"
import os
import json

def get_home_doc(db, description):
    return '''
This page displays contents of database `{0}.db` generated by [this DSC]({0}.html).

{1}
'''.format(os.path.splitext(os.path.basename(db))[0], '' if description is None else '\n\n'.join(description))

def write_notebook(text, output, execute = False):
    import nbformat
    nb = nbformat.reads(text, as_version = 4)
    if execute:
        from nbconvert.preprocessors import ExecutePreprocessor
        ep = ExecutePreprocessor(timeout=600, kernel_name='SoS')
        ep.preprocess(nb, {})
    with open(os.path.expanduser(output), 'wt') as f:
        nbformat.write(nb, f)

def get_database_notebook(db, output, title = "Database Summary", description = None, limit = -1):
    import pickle
    data = pickle.load(open(os.path.expanduser(db), 'rb'))
    jc = JupyterComposer()
    jc.add("# {}\n{}".format(title, get_home_doc(db, description)))
    nn = '\n'
    jc.add(f"Pipelines:\n\n{nn.join([nn.join(['* ' + kk.replace('+', ' -> ') for kk in data[key]]) for key in data if key.startswith('pipeline_')])}")
    jc.add(f"Modules:\n\n{nn.join(['* ' + key for key in data if not key.startswith('pipeline_') and not key.startswith('.')])}")
    jc.add('''
import pickle
data = pickle.load(open("{}", 'rb'))
    '''.format(os.path.expanduser(db)), cell = "code", out = False)
    jc.add("## Pipelines")
    for key in data:
        if key.startswith('pipeline_'):
            for kk in data[key]:
                jc.add(f"### pipeline ``{' -> '.join(kk.split('+'))}``")
                jc.add(f"%preview -n data['{key}']['{kk}'] --limit {limit}", cell = "code")
    jc.add("## Modules")
    for key in data:
        if not key.startswith("pipeline_") and not key.startswith('.'):
            jc.add("### module `{}`".format(key))
            jc.add(f"%preview -n data['{key}'] --limit {limit}", cell = "code")
    if '.html' in data:
        with open(os.path.basename(db)[:-3] + '.html', 'w') as f:
            f.write(data['.html'])
    write_notebook(jc.dump(), output)

def get_query_notebook(db, queries, output, title, description = None, language = None, addon = None, limit = -1):
    jc = JupyterComposer()
    jc.add("# {}\n{}".format(title, get_home_doc(db, description)))
    jc.add('''
import pandas as pd
xls = pd.ExcelFile('{}')
info = [xls.parse(x) for x in xls.sheet_names]
    '''.format(os.path.expanduser(db)), cell = "code", out = False)
    if len(queries) > 1:
        jc.add("## Merged")
        jc.add(f"%preview -n info[0] --limit {limit}", cell = "code")
    for i, q in enumerate(queries):
        jc.add(f"## Pipeline {i+1}" if len(queries) > 1 else "## Merged")
        jc.add("```sql\n{}\n```".format(q), out = False)
        jc.add(f"%preview -n info[{i+1 if len(queries) > 1 else 0}] --limit {limit}", cell = "code")
    if language is not None:
        if language == 'R':
            jc.add("%use R\ninfo <- readxl::read_excel('{}')".format(db), cell = "code", out = False)
        else:
            jc.add("%use {}\n%get info".format(language), cell = "code", out = False)
        if addon is not None:
            files = [os.path.expanduser(x) for x in addon]
            for item in files:
                if not os.path.isfile(item):
                    raise OSError("Cannot find file ``{}``!".format(item))
                jc.add(open(item).read(), cell = "code", out = False, kernel = language)
    write_notebook(jc.dump(), output)

class JupyterComposer:
    def __init__(self):
        self.text = ['{\n "cells": [']
        self.has_end = False

    def add(self, content, cell = "markdown", kernel = "SoS", out = True):
        content = [x + '\n' for x in content.strip().split("\n")]
        content[-1] = content[-1].rstrip('\n')
        self.text.append('  {\n   "cell_type": "%s",%s\n   %s\n   %s"source": %s' \
                         % (cell, '\n   "execution_count": null,' if cell == "code" else '',
                            self.get_metadata(cell, kernel, out),
                            '"outputs": [],\n   'if cell == 'code' else '',
                            json.dumps(content)))
        self.text.append("  },")

    def dump(self):
        if not self.has_end:
            self.text.append(self.get_footer())
            self.has_end = True
        return '\n'.join(self.text)

    def get_footer(self):
        self.text[-1] = self.text[-1].rstrip().rstrip(',')
        return ''' ],
"metadata": {
  "kernelspec": {
   "display_name": "SoS",
   "language": "sos",
   "name": "sos"
  },
  "language_info": {
   "codemirror_mode": "sos",
   "file_extension": ".sos",
   "mimetype": "text/x-sos",
   "name": "sos",
   "nbconvert_exporter": "sos_notebook.converter.SoS_Exporter",
   "pygments_lexer": "sos"
  },
  "sos": {
   "default_kernel": "SoS",
   "kernels": [
    [
     "Python3",
     "python3",
     "Python3",
     "#FFE771"
    ],
    [
     "R",
     "ir",
     "R",
     "#DCDCDA"
    ],
    [
     "SoS",
     "sos",
     "",
     ""
    ]
   ],
   "panel": {
    "displayed": true,
    "height": 0,
    "style": "side"
   }
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}'''

    @staticmethod
    def get_metadata(cell, kernel, out):
        def get_tag():
            if cell == 'code' and out:
                return "report_output"
            elif cell == 'markdown' and not out:
                return "hide_output"
        #
        out = '"metadata": {\n    "collapsed": false,\n    "kernel": "%s",\n    "scrolled": true,\n    "tags": ["%s"]\n   },' % (kernel, get_tag())
        return out

if __name__ == '__main__':
    # jc = JupyterComposer()
    # jc.add("# Title")
    # jc.add("print(666)", cell = 'code', kernel = 'SoS')
    # jc.add("print(999)", cell = 'code', kernel = 'SoS', out = True)
    # print(jc.dump())
    import sys
    get_database_notebook(sys.argv[1], sys.argv[2])
