#!/usr/bin/env python3

import sys
import click

from troi.utils import discover_patches
from troi.core import list_patches, patch_info, convert_patch_to_command
from troi.content_resolver.cli import cli as resolver_cli, db_file_check, output_playlist
from troi.content_resolver.subsonic import SubsonicDatabase
from troi.content_resolver.lb_radio import ListenBrainzRadioLocal
from troi.content_resolver.playlist import read_jspf_playlist
from troi.local.periodic_jams_local import PeriodicJamsLocal

try:
    sys.path.insert(1, ".")
    import config
except ImportError as err:
    config = None


@click.group()
def cli():
    pass


# Add the "db" submenu
resolver_cli.short_help = "database and content resolution commands sub menu"
cli.add_command(resolver_cli, name="db")


@cli.command(context_settings=dict(ignore_unknown_options=True, ))
@click.argument('patch', type=str)
@click.option('--debug/--no-debug', help="Turn on/off debug statements")
@click.option('--print', '-p', 'echo', help="Show the generated playlist", required=False, is_flag=True)
@click.option('--save', '-s', help="Save the generated playlist", required=False, is_flag=True)
@click.option(
    '--token',
    '-t',
    help="Specify the ListenBrainz user token to upload playlist. See https://listenbrainz.org/profile to get your user token.",
    required=False,
    type=click.UUID)
@click.option('--upload',
              '-u',
              help="Upload the generated playlist to ListenBrainz. Also requires --token option",
              required=False,
              is_flag=True)
@click.option('--created-for', '-c', help="The name of the LB user the playlist was created for. For LB use only.", required=False)
@click.option('--name', '-n', help="Override the default name of the generated playlist", required=False)
@click.option('--desc', '-d', help="Override the default description of the generated playlist", required=False)
@click.option('--min-recordings', '-m', help="The minimum number of playlist required for the playlist", type=int, required=False)
@click.option('--spotify-user-id', help="The spotify user name to upload the playlist to", type=str, required=False)
@click.option('--spotify-token',
              help="The spotify token with the correct permissions required to upload playlists",
              type=str,
              required=False)
@click.option('--spotify-url',
              help="instead of creating a new spotify playlist, update the existing playlist at this url",
              type=str,
              required=False,
              multiple=True)
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def playlist(patch, debug, echo, save, token, upload, args, created_for, name, desc, min_recordings, spotify_user_id, spotify_token,
             spotify_url):
    """
    Generate a global MBID based playlist using a patch
    """
    patchname = patch
    patches = discover_patches()
    if patchname not in patches:
        print("Cannot load patch '%s'. Use the list command to get a list of available patches." % patchname, file=sys.stderr)
        return None

    patch_args = {
        "echo": echo,
        "save": save,
        "token": token,
        "created_for": created_for,
        "upload": upload,
        "name": name,
        "desc": desc,
        "min_recordings": min_recordings
    }
    if spotify_token:
        patch_args["spotify"] = {
            "user_id": spotify_user_id,
            "token": spotify_token,
            "is_public": True,
            "is_collaborative": False,
            "existing_urls": spotify_url
        }

    if args is None:
        args = []

    cmd = convert_patch_to_command(patches[patchname])
    context = cmd.make_context(patchname, list(args))
    patch_args.update(context.forward(cmd))

    # Create the actual patch, finally
    patch = patches[patchname](patch_args, debug)
    ret = patch.generate_playlist()

    user_feedback = patch.user_feedback()
    if len(user_feedback) > 0:
        print("User feedback:")
        for feedback in user_feedback:
            print(f"  * {feedback}")
        print()

    sys.exit(0 if ret else -1)


@cli.command(name="list")
def list_patches_cli():
    """List all available patches"""
    ret = list_patches()
    sys.exit(0 if ret else -1)


@cli.command(name="info")
@click.argument("patch", nargs=1)
def info(patch):
    """Get info for a given patch"""
    ret = patch_info(patch)
    sys.exit(0 if ret else -1)


@cli.command(name="resolve", context_settings=dict(ignore_unknown_options=True, ))
@click.option("-d", "--db_file", help="Database file for the local collection", required=False, is_flag=False)
@click.option('-t', '--threshold', default=.80, help="Minimum match percentage for metadata matches. Must be 0.0 - 1.0")
@click.option('-u', '--upload-to-subsonic', required=False, is_flag=True, help="upload playlist via subsonic API")
@click.option('-m', '--save-to-m3u', required=False, help="save to specified m3u playlist")
@click.option('-j', '--save-to-jspf', required=False, help="save to specified JSPF playlist")
@click.option('-y', '--dont-ask', required=False, is_flag=True, help="save playlist without asking user")
@click.argument('jspf_playlist')
def resolve(db_file, threshold, upload_to_subsonic, save_to_m3u, save_to_jspf, dont_ask, jspf_playlist):
    """ Resolve a global JSPF playlist with MusicBrainz MBIDs to files in the local collection"""
    db_file = db_file_check(db_file)
    db = SubsonicDatabase(db_file, config)
    db.open()
    lbrl = ListenBrainzRadioLocal()
    playlist = read_jspf_playlist(jspf_playlist)
    lbrl.resolve_playlist(threshold, playlist)
    output_playlist(db, playlist, upload_to_subsonic, save_to_m3u, save_to_jspf, dont_ask)


@cli.command(name="lb-radio", context_settings=dict(ignore_unknown_options=True, ))
@click.option("-d", "--db_file", help="Database file for the local collection", required=False, is_flag=False)
@click.option('-t', '--threshold', default=.80, help="Minimum match percentage for metadata matches. Must be 0.0 - 1.0")
@click.option('-u', '--upload-to-subsonic', required=False, is_flag=True, help="upload playlist via subsonic API")
@click.option('-m', '--save-to-m3u', required=False, help="save to specified m3u playlist")
@click.option('-j', '--save-to-jspf', required=False, help="save to specified JSPF playlist")
@click.option('-y', '--dont-ask', required=False, is_flag=True, help="save playlist without asking user")
@click.argument('mode')
@click.argument('prompt')
def lb_radio(db_file, threshold, upload_to_subsonic, save_to_m3u, save_to_jspf, dont_ask, mode, prompt):
    """Use LB Radio to create a playlist from a prompt, using a local music collection"""
    db_file = db_file_check(db_file)
    db = SubsonicDatabase(db_file, config)
    db.open()
    r = ListenBrainzRadioLocal()
    playlist = r.generate(mode, prompt, threshold)
    try:
        _ = playlist.playlists[0].recordings[0]
    except (KeyError, IndexError, AttributeError):
        db.metadata_sanity_check(include_subsonic=upload_to_subsonic)
        return

    output_playlist(db, playlist, upload_to_subsonic, save_to_m3u, save_to_jspf, dont_ask)


@cli.command("weekly-jams", context_settings=dict(ignore_unknown_options=True, ))
@click.option("-d", "--db_file", help="Database file for the local collection", required=False, is_flag=False)
@click.option('-t', '--threshold', default=.80, help="Minimum match percentage for metadata matches. Must be 0.0 - 1.0")
@click.option('-u', '--upload-to-subsonic', required=False, is_flag=True, help="upload playlist via subsonic API")
@click.option('-m', '--save-to-m3u', required=False, help="save to specified m3u playlist")
@click.option('-j', '--save-to-jspf', required=False, help="save to specified JSPF playlist")
@click.option('-y', '--dont-ask', required=False, is_flag=True, help="save playlist without asking user")
@click.argument('user_name')
def periodic_jams(db_file, threshold, upload_to_subsonic, save_to_m3u, save_to_jspf, dont_ask, user_name):
    "Generate a weekly jams playlist for your local collection"
    db_file = db_file_check(db_file)
    db = SubsonicDatabase(db_file, config)
    db.open()

    pj = PeriodicJamsLocal(user_name, threshold)
    playlist = pj.generate()
    try:
        _ = playlist.playlists[0].recordings[0]
    except (KeyError, IndexError, AttributeError):
        db.metadata_sanity_check(include_subsonic=upload_to_subsonic)
        return

    output_playlist(db, playlist, upload_to_subsonic, save_to_m3u, save_to_jspf, dont_ask)


@cli.command(context_settings=dict(ignore_unknown_options=True, ))
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def test(args):
    """Run unit tests"""
    import pytest
    raise SystemExit(pytest.main(list(args)))


if __name__ == "__main__":
    cli()
    sys.exit(0)
