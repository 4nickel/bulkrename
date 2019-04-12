#!/usr/bin/env /usr/bin/python3
# vim: set fileencoding=utf-8:

import os
import re
import argparse
import hashlib
import magic

# {{{ Arguments

class ModuleAction(argparse.Action):

    def __call__(self, parser, namespace, values, option = None):
        if not namespace.module:
            namespace.module = []
        module = values[0]
        namespace.module.append(module)

description = 'Rename files by numbering them.'
version = '0.1'
parser = argparse.ArgumentParser(description = description)

parser.add_argument('-v', '--verbose', action = 'store_true', help = 'verbose output')
parser.add_argument('-q', '--quiet',   action = 'store_true', help = 'silence output')
parser.add_argument('-m', '--module', action = ModuleAction, help = 'module', nargs = 1)
parser.add_argument('-c', '--commit', action = 'store_true', help = 'actually commit the commands')
parser.add_argument('-l', '--limit', type = int, help = 'limit name length', default = 0)
parser.add_argument('-a', '--algorithm', action = 'store', type = str, help = 'algorithm', default = 'md5', choices = ['md5', 'sha256'])
parser.add_argument('-r', '--regex', type = str, help = 'match REGEX')

DEFAULT_NUMBER = 0
parser.add_argument('-n', '--number',  type = int, action = 'store',
        help = 'start counting from NUMBER', default = DEFAULT_NUMBER)

DEFAULT_FORMAT ='{name}{ext}'
parser.add_argument('-f', '--format',  type = str, action = 'store',
        help = 'rename files according to FORMAT', default = DEFAULT_FORMAT)

parser.add_argument('FILE', type = str, help = 'file to rename', nargs='*')

modules = []
args = parser.parse_args()

# }}}
# {{{ Util

class Status:

    MOVE = 0
    SAME = 1
    FAIL = 2

class Util:

    def same_file(a, b):
        return os.path.realpath(a) == os.path.realpath(b)

    def move_file(s, d, clobber = False):

        if not os.path.isfile(s):
            raise Exception('not found: {}'.format(s))
        if os.path.isfile(d) and not clobber:
            raise Exception('file exists: {}'.format(d))

        os.rename(s, d)

    def file_part(filename):
        split = os.path.splitext(filename)
        return os.path.dirname(split[0]), os.path.basename(split[0]), split[1]

    def file_move(operation):
        src, (path, name) = operation
        dst = name
        if path: dst = '{}/{}'.format(path, name)
        return src, dst

# }}}
# {{{ Modules

class Module:

    def __init__(self, args):
        self.args = args

    def map(self, file_name):
        raise Exception('not implemented')

class NumberModule(Module):

    def __init__(self, args):
        super().__init__(args)
        self.number = args.number

    def map(self, file_name):
        hmap = { 'n': self.number }
        self.number += 1
        return hmap

class HashModule(Module):

    ALGORITHMS = {
        'md5': hashlib.md5,
        'sha256': hashlib.sha256
    }

    def __init__(self, args):
        super().__init__(args)
        self.hash = HashModule.ALGORITHMS[args.algorithm]

    def map(self, file_name):
        a = self.hash()
        with open(file_name, mode = 'rb') as f:
            for line in f: a.update(line)
        return {'hash': a.hexdigest()}

class RegexModule(Module):

    def __init__(self, args):
        super().__init__(args)
        self.regex = re.compile(args.regex)
        self.keys = [name for name, _ in self.regex.groupindex.items()]

    def map(self, file_name):
        hmap = {}
        match = self.regex.search(file_name)
        for key in self.keys:
            pass
        return hmap

class StatModule(Module):

    def __init__(self, args):
        super().__init__(args)

    def map(self, file_name):
        stat = os.stat(file_name)
        return {
            'mode': stat.st_mode,
            'inode': stat.st_ino,
            'device': stat.st_dev,
            'nlink': stat.st_nlink,
            'uid': stat.st_uid,
            'gid': stat.st_gid,
            'size': stat.st_size,
            'atime': stat.st_atime,
            'mtime': stat.st_mtime,
            'ctime': stat.st_ctime,
        }

class MimeModule(Module):

    EXTENSION_MAP = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'video/ogg': '.ogg',
        'video/mp4': '.mp4',
        'audio/mpeg': '.mp3',
        'audio/basic': '.snd',
        'audio/mid': '.mid',
        'audio/x-m4a': '.m4a',
        'video/x-ms-asf': '.wmv',
        'video/x-flv': '.flv',
        'audio/x-aiff': '.aiff',
        'audio/x-mpegurl': '.m3u',
        'audio/x-pn-realaudio': '.ra',
        'audio/x-wav': '.wav',
        'text/xml': '.xml',
        'text/html': '.html',
        'application/pdf': '.pdf',
    }

    def __init__(self, args):
        super().__init__(args)
        self.mime = magic.Magic(mime = True)

    def map(self, file_name):
        mime = self.mime.from_file(file_name)
        if not mime:
            raise Exception('unable to guess mimetype')
        if not mime in MimeModule.EXTENSION_MAP:
            raise Exception('unable to map extension: {}'.format(mime))
        return {'mime': MimeModule.EXTENSION_MAP[mime]}

# }}}
# {{{ Main

class Rename:

    MODULE_MAPPING = {
        'number': NumberModule,
        'regex': RegexModule,
        'hash': HashModule,
        'mime': MimeModule,
        'stat': StatModule,
    }

    def __init__(self, args):
        self.args = args
        self.modules = []

        if args.module:
            for module in args.module:
                if not module in self.MODULE_MAPPING:
                    raise Exception('unknown module: {}'.format(module))
                constructor = self.MODULE_MAPPING[module]
                self.modules.append(constructor(args))

    def file_name(self, file_name):
        path, name, ext = Util.file_part(file_name)
        placeholders = { 'name': name, 'ext': ext }
        for module in self.modules:
            for k, v in module.map(file_name).items():
                if k in placeholders:
                    raise Exception('duplicate key: {}'.format(k))
                placeholders[k] = v
        form = self.args.format.format(**placeholders)
        if self.args.limit > 0:
            form = form[:self.args.limit]
        return path, form

    def process(self, src, dst, status):
        if Util.same_file(src, dst):
            status.append((Status.SAME, None))
        elif not self.args.commit:
            status.append((Status.MOVE, None))
        else:
            try:
                Util.move_file(src, dst)
                status.append((Status.MOVE, None))
            except Exception as err:
                status.append((Status.FAIL, str(err)))

    def summarize(self, report):
        for (src, dst), (val, msg) in report:
            if   val == Status.MOVE: print('[move]: {} <- {}'.format(dst, src))
            elif val == Status.SAME: print('[same]: {} <- {}'.format(dst, src))
            elif val == Status.FAIL: print('[fail]: {} <- {} | {}'.format(dst, src, msg))

    def run(self):
        files = self.args.FILE
        names = [self.file_name(f) for f in files]
        moves = [Util.file_move(m) for m in zip(files, names)]
        status = []
        for src, dst in moves:
            self.process(src, dst, status)
        self.summarize(zip(moves, status))

# }}}

r = Rename(args)
r.run()
