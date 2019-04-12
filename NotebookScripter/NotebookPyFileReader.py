import re

from nbformat.v4 import (
    new_code_cell,
    new_markdown_cell,
    new_notebook
)


CELL_SEPARATOR_RE = r"^#\s*%%"


class VscodePyReader(object):

    def read(self, fp, **kwargs):
        """Read a notebook from a file like object"""
        nbs = fp.read()
        return self.reads(nbs, **kwargs)

    def reads(self, s, **kwargs):
        """Read from a string"""
        return self.to_notebook(s, **kwargs)

    def to_notebook(self, s, **kwargs):
        lines = s.splitlines()
        cells = []
        cell_lines = []
        state = None

        # .match(some_text) should be true if some_text starts with '# %%' with any amount of whitespace after the # and before the %%
        find_cell_start = re.compile(CELL_SEPARATOR_RE)

        for line in lines:
            if find_cell_start.match(line):
                if cell_lines:
                    cell = self.new_cell(state, cell_lines)
                    if cell is not None:
                        cells.append(cell)
                if "[markdown]" in line:
                    state = 'markdowncell'
                    cell_lines = []
                else:
                    state = 'codecell'
                    cell_lines = []
            elif state is not None:
                cell_lines.append(line)
        if cell_lines:
            cell = self.new_cell(state, cell_lines)
            if cell is not None:
                cells.append(cell)
        nb = new_notebook(cells=cells, metadata={'language': 'python'})
        return nb

    def new_cell(self, state, lines, **kwargs):
        if state == 'codecell':
            code_text = u'\n'.join(lines)
            code_text = code_text.strip(u'\n')
            if code_text:
                return new_code_cell(source=code_text)
        elif state == u'markdowncell':
            text = self._remove_comments(lines)
            if text:
                return new_markdown_cell(source=text)

    def _remove_comments(self, lines):
        new_lines = []
        for line in lines:
            if line.startswith(u'#'):
                new_lines.append(line[2:])
            else:
                new_lines.append(line)
        text = u'\n'.join(new_lines)
        text = text.strip(u'\n')
        return text


def read_pyfile_as_notebook(pyfile):
    with open(pyfile) as fp:
        pytext = fp.read()

    decide_if_vscode_style = re.compile(CELL_SEPARATOR_RE, re.MULTILINE)

    if decide_if_vscode_style.match(pytext):
        return read_vscode_pyfile_as_notebook(pytext)
    else:
        return read_legacy_pyfile_as_notebook(pytext)


def read_vscode_pyfile_as_notebook(pytext):
    _reader = VscodePyReader()
    nbook = _reader.reads(pytext)
    return nbook


def read_legacy_pyfile_as_notebook(pytext):
    from nbformat import v3, v4

    pytext += """
    # <markdowncell>

    # If you can read this, reads_py() is no longer broken!
    """

    nbook = v3.reads_py(pytext)
    nbook = v4.upgrade(nbook)  # Upgrade v3 to v4

    return nbook
