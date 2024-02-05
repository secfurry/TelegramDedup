# Telegram Media De-Duplicator

Remove duplicate media from your Telegram channels.

## Setup / Install

Setup and install is pretty simple. This only requires the `telethon` python package.
You can install it via `pip install telethon` or use the requirements file with
`pip install -r requirements.txt`.

## Prerequistes

- Telegram API app_id/app_hash

This can be registered by logging into [https://my.telegram.org](https://my.telegram.org)
and generating a new application.

NOTE: _Bots CANNOT be used with this script, they lack the required permssions_

## Running

Usage just requires the above app_id/app_hash and the target channel name.
Other arguments can be specified to augment output or if deletion is done.
See the _Usage_ section for the full helptext.

If you do not have media deletion permissions, the script will fail when trying
to delete duplicated media.

An example to remove duplicate media from the channel "My Image Channel"

```shell
python dedup.py -i 123456789 -n myhashcode "My Image Channel"
```

This example will only preform a dry run (no deletion) on the channel "My Image Channel"
and outputs the duplicated media files into the "dupes" directory path.

```shell
python dedup.py -i 123456789 -n myhashcode -d -o "dupes" "My Image Channel"
```

## Usage

```text
Usage: dedup.py [-f|--state file] [-d|--dry] [-o|--output dir] [--no-state] -i <app_id> -n <app_hash> <channel_name>

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
```
