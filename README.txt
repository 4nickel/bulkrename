Bulkrename

Rename files in bulk.
Modular, dynamic approach to generating name data.

By default, only prints planned changes.
Excplicitly pass --commit to actually commit.

Usage:
    bulkrename -[vq] -c -l LIMIT -m MODULE <MODULE_FLAGS> -f FORMAT -- [FILE [FILE..]]
    bulkrename --help

The FILEs will be renamed in accordance with FORMAT.
Modules must be enabled explicitly in order to be used.
Many modules provide additional flags to control their
output.

Below are some safe examples of common scenarios:
Pass -c to actually rename files.

Prefix/postfix names
    bulkrename -f 'Cool Stuff {name}.jpg' -- Foo Bar

Will generate
    move 'Foo' -> 'Cool Stuff Foo.jpg'
    move 'Bar' -> 'Cool Stuff Bar.jpg'

Content digest
    bulkrename -m hash -a md5 -f '{hash}{ext}' -- <files>

Incrementing counter
    bulkrename -m number '{number}{ext}' -- <files>

Rename with regex
    bulkrename -m regex -r '(?P<capture>.*)' -f 'your.{capture}.here' -- <files>

Fix mime types
    bulkrename -m mime -f '{name}{mime}' -- <files>

Add stat information
    bulkrename -m stat -f '{name}' -- <files>

Modules
      hash | --algorithm [md5|sha256]   | Select hash algorithm
      mime |
    number | --number N                 | Start counting from N
     regex | --regex REGEX              | Capture REGEX
      stat |

Formatting

Default
      name | Contains the original file name, without extension
      ext  | Contains the original extension. May be empty

Hash
      hash | The digested contents of the file

Mime
      mime | Makes a best-effort guess as to what the correct mime
             type may be and tries to map it to an extension. Use
             with caution, as mime-types may not be detected correctly.
Number
    number | The number N of the file

Regex
           | The regex will be run against every file name. You can
           | access any *named* capture group in the format. Can be
           | quite powerful.

Stat
      'mode' | File mode
     'inode' | Inode number
    'device' | Device
     'nlink' | Number of hardlinks
       'uid' | User ID
       'gid' | Group ID
      'size' | Size in bytes
     'atime' | Last accest time
     'mtime' | Last modification time
     'ctime' | Birth time

TODO:
    - Turn this README into markdown
    - Add more modules
    - Better error handling
    - Automated testing
