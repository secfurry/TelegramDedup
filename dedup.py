#!/usr/bin/python3
#
# Copyright (c) 2024 secfurry
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

from hashlib import md5
from os import makedirs
from sys import stderr, exit, argv
from argparse import ArgumentParser
from telethon.sync import TelegramClient
from os.path import join, exists, isdir, expanduser, expandvars


USAGE = """Telegram Image Deduplicater

Usage: {bin} [-f|--state file] [-d|--dry] [-o|--output dir] [--no-state] -i <app_id> -n <app_hash> <channel_name>

Positional Arguments:
    channel_name            Name of the Channel to use. You MUST have the ability
                            to delete media for deletion to work!

Required Arguments:
    -i           <app_id>   Telegram API app_id value.
    --app-id
    -n           <app_hash> Telegram API app_hash value.
    --app-hash

Optional Arguments:
    -f           <file>     Name of the saved session state file. Used to prevent
    --state                 needing to supply credentials every time used.
    -o           <dir>      Path of a directory to output the duplicated media files
    --output                to. If this directory does not exist, it will be created.
    -d                      Preform a dry run and do not delete any duplicate media.
    --dry                   This will still output files is the "-o/--output" argument
                            is used.
    --no-state              Prevent using a state file. By default if no "-f/--state"
                            argument is provided, the value "deduper" will be used.
                            pass this flag to prevent this default state file from
                            being used. Overrides any "-f/--state" argument.

The app_id and app_hash values can be gerenerated via the Telegram API page at
https://my.telegram.org.

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
        "-f",
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
        "-o",
        "--output",
        type=str,
        dest="output",
        action="store",
        required=False,
    )
    p.add_argument(
        "-d",
        "--dry",
        dest="dry",
        action="store_true",
        required=False,
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
    a = p.parse_args()
    del p
    if len(a.name) != 1:
        raise ValueError("name cannot be empty")
    n = a.name[0]
    if not isinstance(n, str) or len(n) == 0:
        raise ValueError("name cannot be empty")
    if not isinstance(a.app_hash, str) or len(a.app_hash) == 0:
        raise ValueError("app_hash cannot be empty")
    if isinstance(a.output, str) and len(a.output) > 0:
        d = expandvars(expanduser(a.output))
        if exists(d) and not isdir(d):
            raise ValueError(f'output "{d}" is not a directory')
        makedirs(d, exist_ok=True)
    else:
        d = None
    if a.no_state:
        s = None
    else:
        s = a.state
    with TelegramClient(s, a.app_id, a.app_hash) as x:
        c = _find_channel(x, n)
        if c is None:
            raise ValueError(f'no channel with name "{a.name}" found')
        print(f'Found Channel "{c.name}" with ID {c.id}..')
        _check_duplicates(x, c, a.dry, d)
        del c
    del s, d, n


def _usage():
    print(USAGE.format(bin=argv[0]))
    exit(2)


def _find_channel(client, name):
    for i in client.get_dialogs():
        if not i.is_channel or i.is_group:
            continue
        if i.name != name:
            continue
        return i
    return None


def _check_duplicates(client, channel, dry, output):
    e = dict()
    for i in client.iter_messages(channel.id, reverse=True):
        if i.file is None:
            continue
        z = md5(usedforsecurity=False)
        b = i.download_media(bytes, thumb=None)
        z.update(b)
        h = z.hexdigest()
        del z
        if h not in e:
            e[h] = list()
        else:
            print(f"Duplicate of {h} detected in Message {i.id}..")
            if output is not None:
                n = len(e[h])
                if n == 1:
                    e[h][0].download_media(join(output, f"{h}-0.jpg"), thumb=None)
                with open(join(output, f"{h}-{n}.jpg"), "wb") as f:
                    f.write(b)
                del n
        e[h].append(i)
        del b, h
    if dry:
        print("Dry run, not deleting anything..")
    n = 0
    for k, v in e.items():
        if len(v) == 1:
            continue
        print(f"Duplicates of {k}: {len(v)}")
        for x in range(0, len(v)):
            if x == 0:
                print(f"\tMessage: {v[x].id} (Original)")
            else:
                if not dry:
                    v[x].delete()
                print(f"\tMessage {v[x].id}")
        n += 1
    print(f"{n} Duplicate Media entries found!")
    del e, n


if __name__ == "__main__":
    try:
        _main()
    except Exception as err:
        print(f"Error during runtime: {err}!", file=stderr)
        exit(1)
