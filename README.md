# Bulkrename

&nbsp;
> I wrote this for personal usage - it is simple enough and has proven useful. I'd be happy to hear your feedback and ideas for improvement. Cheers!

&nbsp;

The main idea is to have a modular, dynamic approach to generating filenames. In order to keep a good performance profile, modules must be enabled explicitly to be used. Many modules accept additional flags to control their output.

The tool ships with a variety of specialized modules for renaming e.g. fonts or images, and more general ones - such as content-digests, simple counters or regex captures. By default, planned changes are only printed, and no action is taken. Pass ``--commit`` to actually rename any files.

Usage:
```sh
bulkrename -[vq] -c -l LIMIT -m MODULE <OPTIONS> -f FORMAT -- [FILE [FILE..]]
bulkrename --help
```

Files are renamed in accordance with the given ``FORMAT`` string.



#### Examples

Add prefix/suffix:
```sh
$ bulkrename -f 'prefix-{name}{ext}' -- ..files..
$ bulkrename -f '{name}-suffix{ext}' -- ..files..
```
Content digest - in this case the md5 algorithm is used:
```sh
bulkrename -m hash -a md5 -f '{hash}{ext}' -- ..files..
```

Incrementing counter - files are numbered in the order they appear as arguments:
```sh
bulkrename -m number '{number}{ext}' -- ..files..
```

Rename with regex:
```sh
bulkrename -m regex -r '(?P<capture>.*)' -f 'your.{capture}.here' -- ..files..
```

Fix mime types:
```sh
bulkrename -m mime -f '{name}{mime}' -- ..files..
```

Add mtime or other file stats:
```sh
bulkrename -m stat -f '{name}-{mtime}{ext}' -- ..files..
```

Image width and height:
```sh
bulkrename -m image -f '{name}_{width}x{height}{ext}' -- ..files..
```

#### Module Overview:
Module | Description | Arguments | &nbsp;
--- | --- | --- | ---
hash | Content digest |  --algorithm [md5\|sha256]   | Select algorithm
mime | Try to detect MIME type | |
number | Simple counter | --number N  | Start counting from N
regex  | Capture via regex | --regex REGEX  | Regex to use
stat | Unix file stat command | |
image | Image dimensions | |
font | Font information | |

#### Formatting

##### default:

Format | Description
--- | ---
name | Contains the original file name, without extension
ext  | Contains the original extension. May be empty

##### hash:

Format | Description
--- | ---
hash | The content digest

##### mime:

Format | Description
--- | ---
mime | Best-effort guess of the MIME-type. May be incorrect!

##### number:

Format | Description
--- | ---
number | The number N of the file

##### regex:

> The regex will be run against every file name. You can access any *named* capture group in the format string. Very flexible and powerful.

##### stat:

Format | Description
--- | ---
mode | File mode
inode | Inode number
device | Device
nlink | Number of hardlinks
uid | User ID
gid | Group ID
size | Size in bytes
atime | Last accest time
mtime | Last modification time
ctime | Birth time

##### image:

Format | Description
--- | ---
width | The width of the image file in pixels
height | The height of the image file in pixels
ratio | The ratio of width to height

#### TODO:
* More modules
* Add tests