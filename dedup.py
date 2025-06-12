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

from PIL import Image
from os import makedirs
from struct import pack
from imagehash import dhash
from hashlib import md5, sha256
from io import BytesIO, StringIO
from sys import stderr, exit, argv
from argparse import ArgumentParser
from telethon.sync import TelegramClient
from telethon.tl.types import PeerUser, PeerChannel, PeerChat
from os.path import join, exists, isdir, expanduser, expandvars


USAGE = """Telegram Chat Text/File/Image/Video De-Duplicator

Usage: {bin} [-s|--state file] [-d|--dry] [-o|--output dir] [--no-state] -i <app_id> -n <app_hash> <channel_name>

Positional Arguments:
    channel_name            Name of the Channel to use. You MUST have the ability
                            to delete media for deletion to work!

Required Arguments:
    -i           <app_id>   Telegram API "app_id" value.
    --app-id
    -n           <app_hash> Telegram API "app_hash" value.
    --app-hash

Optional Arguments:
    -s           <file>     Name of the saved session state file. Used to prevent
    --state                  needing to supply credentials every time used.
    -o           <dir>      Path of a directory to output the duplicated media files
    --output                 to. If this directory does not exist, it will be created.
                             If the "--text" option is used, this will add a "text.log"
                             file in the directory
    -d                      Preform a dry run and do not delete any duplicate media.
    --dry                    This will still output files is the "-o/--output" argument
                             is used.
    --text                  Also De-duplicate Text Messages. These will be compared
                             using a different dict to prevent collisions with
                             media.
    --user                  Use poster as an additional filter when searching. This
                             will only find/delete duplicates from messages by the
                             same user. Duplicates made by other users will not be
                             affected.
    --no-media              Prevent check for duplicate Photo/Video/File entries. This
                             imples "--text".
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
        "--text",
        dest="text",
        action="store_true",
        required=False,
    )
    p.add_argument(
        "--no-media",
        dest="no_media",
        action="store_true",
        required=False,
    )
    p.add_argument(
        "--user",
        dest="user",
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
            raise ValueError(f'no Channel or Group with name "{n}" found')
        print(
            f'Found {'Channel' if c.is_channel else 'Group'} "{c.name}" with ID {c.id}..'
        )
        _check_duplicates(x, c, a.dry, d, a)
        del c
    del s, d, n


def _usage(*_):
    print(USAGE.format(bin=argv[0]))
    exit(2)


def _get_user(m):
    if isinstance(m.from_id, PeerChat):
        return m.from_id.chat_id
    elif isinstance(m.from_id, PeerUser):
        return m.from_id.user_id
    elif isinstance(m.from_id, PeerChannel):
        return m.from_id.channel_id
    return None


def _find_channel(client, name):
    for i in client.get_dialogs():
        if not i.is_channel and not i.is_group:
            continue
        if i.name != name:
            continue
        return i
    return None


def _check_duplicates(client, channel, dry, output, args):
    e, o, t, y = dict(), 0, dict(), args.text or args.no_media
    for i in client.iter_messages(channel.id, reverse=True):
        o += 1
        if i.file is None:
            if not y or not isinstance(i.raw_text, str) or len(i.raw_text) == 0:
                continue
            z = sha256(usedforsecurity=False)
            if args.user:
                u = _get_user(i)
                if u is not None:
                    z.update(pack("<Q", u))
                del u
            z.update(i.raw_text.encode("UTF-8"))
            h = z.hexdigest()
            del z
            if h not in t:
                t[h] = list()
            else:
                print(f"[ Text] Duplicate of {h} detected in Message {i.id}..")
            t[h].append(i)
            del h
            continue
        if args.no_media:
            continue
        b = i.download_media(file=bytes, thumb=None)
        try:
            with Image.open(BytesIO(b)) as f:
                h = str(dhash(f))
        except Exception:
            z = md5(usedforsecurity=False)
            if args.user:
                u = _get_user(i)
                if u is not None:
                    z.update(pack("<Q", u))
                del u
            z.update(b)
            h = z.hexdigest()
            del z
        else:
            if args.user:
                u = _get_user(i)
                if u is not None:
                    h = f"{h}{u:x}"
                del u
        if h not in e:
            e[h] = list()
        else:
            print(
                f"{'[Media] ' if y else ''}Duplicate of {h} detected in Message {i.id}.."
            )
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
    del y
    n = 0
    for k, v in e.items():
        if len(v) == 1:
            continue
        print(f"Duplicates of {k}: {len(v)}")
        for x in range(0, len(v)):
            if x == 0:
                print(
                    f"\tMessage ({v[x].date.strftime("%m/%d/%y %H:%M")}): {v[x].id} (Original)"
                )
            else:
                if not dry:
                    v[x].delete()
                print(f"\tMessage ({v[x].date.strftime("%m/%d/%y %H:%M")}): {v[x].id}")
        n += 1
    print(f"{n} Duplicate Media entries found!")
    n, b = 0, StringIO()
    for k, v in t.items():
        if len(v) == 1:
            continue
        print(f"Duplicates of {k}: {len(v)}")
        b.write(
            f"Duplicate Hash ({k}), Created: ({v[0].date.strftime("%m/%d/%y %H:%M")}), "
            f"Content: [\n{v[0].raw_text}\n]\n{'=' * 64}\n"
        )
        for x in range(0, len(v)):
            if x == 0:
                print(
                    f"\tMessage: ({v[x].date.strftime("%m/%d/%y %H:%M")}) {v[x].id:6} (Original)"
                )
                b.write(
                    f" {x:4} - ({v[x].date.strftime("%m/%d/%y %H:%M")}) {v[x].id:6}: {v[x].id} (Original)\n"
                )
            else:
                if not dry:
                    v[x].delete()
                print(f"\tMessage ({v[x].date.strftime("%m/%d/%y %H:%M")}) {v[x].id:6}")
                b.write(
                    f" {x:4} - ({v[x].date.strftime("%m/%d/%y %H:%M")}) {v[x].id:6} : {v[x].id}\n"
                )
        b.write("\n")
    if output is not None and b.tell() > 0:
        try:
            with open(join(output, "text.log"), "w") as f:
                f.write(b.getvalue())
        except OSError as err:
            # Don't fail the entire thing if this borks.
            print(f"Error saving text data: {err}")
    b.close()
    del b, e, n


if __name__ == "__main__":
    try:
        _main()
    except Exception as err:
        print(f"Error during runtime: {err}!", file=stderr)
        exit(1)
