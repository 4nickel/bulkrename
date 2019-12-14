from bulkrename import Rename, Status


FILES = [
    "test/foo.txt",
    "test/bar.txt",
    "test/baz.txt",
]


class RenameArgs:
    """Mock-up of command-line argument data. It would be nice to get rid of this."""

    def __init__(self, files=None, commit=False, module=None,
                 number=0, format_string=None, algorithm=None):
        if module is None:
            module = []
        if format_string is None:
            format_string = "{name}{ext}"
        if algorithm is None:
            algorithm = "md5"
        if files is None:
            files = FILES.copy()
        self.module = module
        self.number = number
        self.algorithm = algorithm
        self.format = format_string
        self.commit = commit
        self.limit = 0
        self.FILE = files


def test_no_clobber():
    """Check if we detect clobbering."""
    r = Rename.from_arguments(RenameArgs(
        format_string="bar.txt",
        commit=True,
    ))
    _moves, status = r.run()
    assert status[0][0] == Status.FAIL
    assert status[1][0] == Status.SAME
    assert status[2][0] == Status.FAIL


def test_same_name():
    """Check if we detect moves to the same file."""
    r = Rename.from_arguments(RenameArgs())
    moves, status = r.run()
    assert moves[0][0] == moves[0][1]
    assert moves[1][0] == moves[1][1]
    assert moves[2][0] == moves[2][1]
    assert status[0][0] == Status.SAME
    assert status[1][0] == Status.SAME
    assert status[2][0] == Status.SAME


def test_number_module_default():
    """Check the 'number' modules basic functionality with no fancy formatting."""
    r = Rename.from_arguments(RenameArgs(
        module=["number"],
        format_string='{n}{ext}',
        number=0,
    ))
    moves, status = r.run()
    assert moves[0][1] == "test/0.txt"
    assert moves[1][1] == "test/1.txt"
    assert moves[2][1] == "test/2.txt"
    assert status[0][0] == Status.MOVE
    assert status[1][0] == Status.MOVE
    assert status[2][0] == Status.MOVE


def test_hash_module_md5():
    """Check the 'hash' modules md5 format."""
    r = Rename.from_arguments(RenameArgs(
        module=["hash"],
        format_string='{hash}{ext}',
        algorithm="md5",
    ))
    moves, status = r.run()
    name = "test/d41d8cd98f00b204e9800998ecf8427e.txt"
    assert moves[0][1] == name
    assert moves[1][1] == name
    assert moves[2][1] == name
    assert status[0][0] == Status.MOVE
    assert status[1][0] == Status.MOVE
    assert status[2][0] == Status.MOVE


def test_hash_module_sha256():
    """Check the 'hash' modules sha256 format."""
    r = Rename.from_arguments(RenameArgs(
        module=["hash"],
        format_string='{hash}{ext}',
        algorithm="sha256",
    ))
    moves, status = r.run()
    name = "test/e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.txt"
    assert moves[0][1] == name
    assert moves[1][1] == name
    assert moves[2][1] == name
    assert status[0][0] == Status.MOVE
    assert status[1][0] == Status.MOVE
    assert status[2][0] == Status.MOVE
