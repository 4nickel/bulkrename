#!/usr/bin/env python3
# vim: set fileencoding=utf-8:

import argparse
import hashlib
import os
import re
from abc import ABC, abstractmethod

import magic
from PIL import Image
from fontTools import ttLib


class ModuleException(Exception):
    """"An error occured in one of the modules."""


class UnknownModuleException(Exception):
    """"The user asked to load an unkown module."""


class RenderError(Exception):
    """"An error occurred while rendering a new file name."""


class MimeError(Exception):
    """"An error occurred in the 'mime' module."""


class ClobberError(Exception):
    """"It is an error to clobber a file without being asked to."""


class FileError(Exception):
    """"An error happened when operating on a file."""


def same_file(a_file: str, b_file: str):
    """"Check if two paths resolve to the same file."""
    return os.path.realpath(a_file) == os.path.realpath(b_file)


def move_file(src_file: str, dst_file: str, clobber: bool = False):
    """"Rename a file. Only clobber stuff when asked to."""
    # NOTE: Yes, there is a race-condition here. Just ignore it for now.
    if not os.path.isfile(src_file):
        raise FileError('no such file: {}'.format(src_file))
    if os.path.isfile(dst_file) and not clobber:
        raise ClobberError('file exists: {}'.format(dst_file))
    os.rename(src_file, dst_file)


def split_dir_file_ext(file_name: str):
    """"Split a path into three strings: directory name, file name and extension."""
    split = os.path.splitext(file_name)
    return os.path.dirname(split[0]), os.path.basename(split[0]), split[1]


class Status:
    """"Enum of possible operation statuses."""

    MOVE = 0
    SAME = 1
    FAIL = 2


class Module(ABC):
    """"Abstract base-class for modules."""

    def __init__(self, args):
        self.args = args

    @abstractmethod
    def placeholders(self, file_name: str):
        """"Create placeholders for the given file."""
        raise NotImplementedError


class ImageModule(Module):
    """"This module provides renaming based on image metadata."""

    def placeholders(self, file_name: str):
        """"Create placeholders for the given file."""
        img = Image.open(file_name)
        width, height = img.size
        return {
            'height': height,
            'width': width,
            'ratio': width/height,
        }


class NumberModule(Module):
    """"This module provides renaming based on numbering."""

    def __init__(self, args):
        super().__init__(args)
        self.number = args.number

    def placeholders(self, file_name: str):
        """"Create placeholders for the given file."""
        placeholders = {'n': self.number}
        self.number += 1
        return placeholders


class HashModule(Module):
    """"This module provides renaming based on content-digests."""

    ALGORITHMS = {
        'md5': hashlib.md5,
        'sha256': hashlib.sha256
    }

    def __init__(self, args):
        super().__init__(args)
        self.hash = HashModule.ALGORITHMS[args.algorithm]

    def placeholders(self, file_name: str):
        """"Create placeholders for the given file."""
        digest = self.hash()
        with open(file_name, mode='rb') as fd:
            for line in fd:
                digest.update(line)
        return {'hash': digest.hexdigest()}


class RegexModule(Module):
    """"This module provides renaming based on regex matching."""

    def __init__(self, args):
        super().__init__(args)
        self.regex = re.compile(args.regex)
        self.keys = [name for name, _ in self.regex.groupindex.items()]

    def placeholders(self, file_name: str):
        """"Create placeholders for the given file."""
        placeholders = {}
        match = self.regex.search(file_name)
        for key in self.keys:
            placeholders[key] = match.group(key)
        return placeholders


class StatModule(Module):
    """"This module provides renaming based on the `stat` command."""

    def placeholders(self, file_name: str):
        """"Create placeholders for the given file."""
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
    """"This module provides renaming based on MIME types."""

    # This should really go into a data file.
    EXTENSIONS = {
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
        self.mime = magic.Magic(mime=True)

    def placeholders(self, file_name: str):
        """"Create placeholders for the given file."""
        mime = self.mime.from_file(file_name)
        if not mime:
            raise MimeError('unable to guess mimetype')
        if mime not in MimeModule.EXTENSIONS:
            raise MimeError('unable to map extension: {}'.format(mime))
        return {'mime': MimeModule.EXTENSIONS[mime]}


class FontModule(Module):
    """"This module provides renaming based on font metadata."""

    FONT_SPECIFIER_FAMILY_ID = 1
    FONT_SPECIFIER_WEIGHT_ID = 2
    FONT_SPECIFIER_STRING_ID = 3
    FONT_SPECIFIER_NAME_ID = 4

    EXTENSIONS = {
        '.ttf': ttLib.TTFont,
    }

    def placeholders(self, file_name: str):
        """"Create placeholders for the given file."""
        name, extension = os.path.splitext(file_name)
        font = FontModule.EXTENSIONS[extension]
        family, weight, string, name = FontModule.short_name(font(file_name))
        return {
            'font_family': family,
            'font_weight': weight,
            'font_string': string,
            'font_name':   name,
        }

    @staticmethod
    def short_name(font):
        """Get the short name from the font's names table"""

        def decode_unicode(unicode):
            """Decode the unicode and try to be smart about detecting UTF-16."""
            if b'\x00' in unicode.string:
                return unicode.string.decode('utf-16-be')
            return unicode.string.decode('utf-8')

        name, string, family, weight = "", "", "", ""
        for record in font['name'].names:
            decoded = decode_unicode(record)
            if record.nameID == FontModule.FONT_SPECIFIER_FAMILY_ID and not family:
                family = decoded
            elif record.nameID == FontModule.FONT_SPECIFIER_WEIGHT_ID and not weight:
                weight = decoded
            elif record.nameID == FontModule.FONT_SPECIFIER_STRING_ID and not weight:
                string = decoded
            elif record.nameID == FontModule.FONT_SPECIFIER_NAME_ID and not name:
                name = decoded
            if string and family and weight and name:
                break
        return family, weight, string, name


class Rename:
    """"Implements file renaming via a CLI."""

    MODULES = {
        'number': NumberModule,
        'regex': RegexModule,
        'hash': HashModule,
        'mime': MimeModule,
        'stat': StatModule,
        'font': FontModule,
        'image': ImageModule,
    }

    def __init__(self, args=None, modules=None):
        if modules is None:
            modules = []
        if args is None:
            args = {}
        self.modules = modules
        self.args = args

    @staticmethod
    def from_arguments(args):
        """Create a new instance from command-line arguments."""
        modules = []
        if args.module:
            for module in args.module:
                if module not in Rename.MODULES:
                    raise UnknownModuleException(module)
                constructor = Rename.MODULES[module]
                modules.append(constructor(args))
        return Rename(args=args, modules=modules)

    def move_file(self, src: str, dst: str, status):
        """
        Rename a file conditionally, if --commit was passed and keep record of our status.
        """
        if same_file(src, dst):
            status.append((Status.SAME, None))
        elif not self.args.commit:
            status.append((Status.MOVE, None))
        else:
            try:
                move_file(src, dst)
                status.append((Status.MOVE, None))
            except FileError as err:
                status.append((Status.FAIL, str(err)))
            except ClobberError as err:
                status.append((Status.FAIL, str(err)))
            except OSError as err:
                status.append((Status.FAIL, str(err)))

    @staticmethod
    def summarize(report):
        """Print a summary of the result status."""
        for (src, dst), (val, msg) in report:
            if val == Status.MOVE:
                print('[move]: {} <- {}'.format(dst, src))
            elif val == Status.SAME:
                print('[same]: {} <- {}'.format(dst, src))
            elif val == Status.FAIL:
                print('[fail]: {} <- {} | {}'.format(dst, src, msg))

    @staticmethod
    def create_move(operation):
        """Create a move from an operation."""
        src, (path, name) = operation
        dst = name
        if path:
            dst = '{}/{}'.format(path, name)
        return src, dst

    def create_name(self, file_name: str):
        """Generate a new name for the file."""

        path, name, ext = split_dir_file_ext(file_name)
        placeholders = {'name': name, 'ext': ext}
        for module in self.modules:
            for k, v in module.placeholders(file_name).items():
                if k in placeholders:
                    raise RenderError('duplicate key: {}'.format(k))
                placeholders[k] = v

        try:
            rendered = self.args.format.format(**placeholders)
            if self.args.limit > 0:
                rendered = rendered[:self.args.limit]
            return path, rendered
        except KeyError as err:
            raise RenderError('failed to render string: {}'.format(str(err)))

    def run(self):
        """Run the CLI."""
        files = self.args.FILE
        names = [self.create_name(f) for f in files]
        moves = [self.create_move(m) for m in zip(files, names)]
        status = []
        for src, dst in moves:
            self.move_file(src, dst, status)
        return moves, status

    def print_report(self, moves, status):
        """Print a report of resulting moves and status."""
        self.summarize(zip(moves, status))


class ModuleArgumentAction(argparse.Action):
    """"This action gets called for every module specified on the CLI."""

    def __call__(self, parser, namespace, values, option=None):
        if not namespace.module:
            namespace.module = []
        module = values[0]
        namespace.module.append(module)


def main():
    """"
    Main entry point.
    Exists mostly to shut up pylint about globals and constants.
    """

    description = 'Rename files by numbering them.'
    # version = '0.1'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose output')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='silence output')
    parser.add_argument('-m', '--module', action=ModuleArgumentAction,
                        help='module', nargs=1)
    parser.add_argument('-c', '--commit', action='store_true',
                        help='actually commit the commands')
    parser.add_argument('-l', '--limit', type=int,
                        help='limit name length', default=0)
    parser.add_argument('-a', '--algorithm', action='store', type=str,
                        help='algorithm', default='md5', choices=['md5', 'sha256'])
    parser.add_argument('-r', '--regex', type=str, help='match REGEX')
    parser.add_argument('-n', '--number', type=int, action='store',
                        help='start counting from NUMBER', default=0)
    parser.add_argument('-f', '--format', type=str, action='store',
                        help='rename files according to FORMAT', default="{name}{ext}")
    parser.add_argument('FILE', type=str, help='file to rename', nargs='*')

    args = parser.parse_args()
    r = Rename.from_arguments(args)
    moves, status = r.run()
    r.print_report(moves, status)


main()
