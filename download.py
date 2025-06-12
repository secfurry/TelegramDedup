#!/usr/bin/python3
#
# Copyright (c) 2025 secfurry
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

from os import makedirs
from hashlib import md5
from sys import stderr, exit, argv
from argparse import ArgumentParser
from telethon.sync import TelegramClient
from os.path import join, exists, isdir, expanduser, expandvars


USAGE = """Telegram Chat Media Downloader

Usage: {bin} [-f|--state file] [--no-state] -i <app_id> -n <app_hash> <channel_name> <output_dir>

Positional Arguments:
    channel_name            Name of the Channel to use.

    output_dir              Path of a directory to output the duplicated media files
                             to. If this directory does not exist, it will be created.

Required Arguments:
    -i           <app_id>   Telegram API "app_id" value.
    --app-id
    -n           <app_hash> Telegram API "app_hash" value.
    --app-hash

Optional Arguments:
    -f           <file>     Name of the saved session state file. Used to prevent
    --state                  needing to supply credentials every time used.
    --no-state              Prevent using a state file. By default if no "-f/--state"
                             argument is provided, the value "deduper" will be used.
                             pass this flag to prevent this default state file from
                             being used. Overrides any "-f/--state" argument.

The app_id and app_hash values can be gerenerated via the Telegram API page at
https://my.telegram.org

On first run or when no state file is used, you will be asked for Telegram login
credentials. You may use the credentials of any account that has delete permission
for media in the target Telegram channel.

NOTE: YOU CANNOT USE BOT TOKENS FOR THIS!! Bots do NOT have the ability to list
channels.
"""


def _main():
    p = ArgumentParser()
    p.print_help = _usage
    p.print_usage = _usage
    p.add_argument(
        "-s",
        "--state",
        type=str,
        dest="state",
        action="store",
        default="deduper",
        required=False,
    )
    p.add_argument(
        "-i",
        "--app-id",
        type=int,
        dest="app_id",
        action="store",
        required=True,
    )
    p.add_argument(
        "-n",
        "--app-hash",
        type=str,
        dest="app_hash",
        action="store",
        required=True,
    )
    p.add_argument(
        "--no-state",
        dest="no_state",
        action="store_true",
        required=False,
    )
    p.add_argument(
        type=str,
        dest="name",
        nargs=1,
        action="store",
    )
    p.add_argument(
        type=str,
        dest="output",
        nargs=1,
        action="store",
    )
    a = p.parse_args()
    del p
    if len(a.name) != 1:
        raise ValueError('"name" cannot be empty')
    if len(a.output) != 1:
        raise ValueError('"output" cannot be empty')
    n, o = a.name[0], a.output[0]
    if not isinstance(n, str) or len(n) == 0:
        raise ValueError("name cannot be empty")
    if not isinstance(a.app_hash, str) or len(a.app_hash) == 0:
        raise ValueError("app_hash cannot be empty")
    if not isinstance(o, str) and len(o) == 0:
        raise ValueError("output cannot be empty")
    d = expandvars(expanduser(o))
    if exists(d) and not isdir(d):
        raise ValueError(f'output "{d}" is not a directory')
    makedirs(d, exist_ok=True)
    if a.no_state:
        s = None
    else:
        s = a.state
    with TelegramClient(s, a.app_id, a.app_hash) as x:
        c = _find_channel(x, n)
        if c is None:
            raise ValueError(f'no Channel or Group with name "{n}" found')
        print(
            f'Found {'Channel' if c.is_channel else 'Group'} "{c.name}" with ID {c.id}..'
        )
        _check_duplicates(x, c, d)
        del c
    del s, d, n


def _usage(*_):
    print(USAGE.format(bin=argv[0]))
    exit(2)


def _find_channel(client, name):
    for i in client.get_dialogs():
        if not i.is_channel and not i.is_group:
            continue
        if i.name != name:
            continue
        return i
    return None


def _check_duplicates(client, channel, output):
    e, o = dict(), 0
    for i in client.iter_messages(channel.id, reverse=True):
        if i.file is None:
            continue
        z = md5(usedforsecurity=False)
        if o % 10 == 0:
            print(f"Downloading item {o}..")
        b = i.download_media(bytes, thumb=None)
        z.update(b)
        h = z.hexdigest()
        del z
        if h in e:
            print(f"Duplicate of {h} detected in Message {i.id}..")
            continue
        e[h] = True
        if i.file.mime_type == "video/mp4":
            n = "mp4"
        else:
            n = "jpg"
        with open(join(output, f"{o}-{h}.{n}"), "wb") as f:
            f.write(b)
        del b, h, n
        o += 1


if __name__ == "__main__":
    try:
        _main()
    except Exception as err:
        print(f"Error during runtime: {err}!", file=stderr)
        exit(1)
