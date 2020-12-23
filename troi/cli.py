#!/usr/bin/env python3

import sys
import click
import pytest

import troi
import troi.playlist
import troi.utils
from troi.patches.ab_similar_recordings import ABSimilarRecordingsPatch


@click.group()
def cli():
    pass


@cli.command(context_settings=dict(
    ignore_unknown_options=True,
))
@click.argument('patch', type=str)
@click.option('--debug/--no-debug')
@click.option('--print', '-p', 'echo', required=False, is_flag=True)
@click.option('--save', '-s', required=False, is_flag=True)
@click.option('--token', '-t', required=False, type=click.UUID)
@click.option('--created-for', '-c', required=False)
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def playlist(patch, debug, echo, save, token, args, created_for):
    """
    Generate a playlist using a patch

    \b
    PRINT: This option causes the generated playlist to be printed to stdout.
    SAVE: The save option causes the generated playlist to be saved to disk.
    TOKEN: Specifying a token submits the playlists to ListenBrainz. This must be the token of
           the user whose account the playlist is being submitted to. See https://listenbrainz.org/profile to
           get your user token.
    CREATED-FOR: If this option is specified, it must give a valid user name and the
                 TOKEN argument must specify a user who is whitelisted as a playlist bot at
                 listenbrainz.org .
    """

    patchname = patch
    patches = troi.utils.discover_patches()
    if patch not in patches:
        print("Cannot load patch '%s'. Use the list command to get a list of available patches." % patch,
              file=sys.stderr)
        sys.exit(1)

    patch = patches[patch](debug)

    context = patch.parse_args.make_context(patchname, list(args))
    pipelineargs = context.forward(patch.parse_args)
    pipeline = patch.create(pipelineargs)

    try:
        playlist = troi.playlist.PlaylistElement()
        playlist.set_sources(pipeline)
        playlist.generate()
    except troi.PipelineError as err:
        print("Failed to generate playlist: %s" % err,
              file=sys.stderr)
        sys.exit(2)

    if token:
        for url, _ in playlist.submit(token, created_for):
            print("Submitted playlist: %s" % url)

    if save:
        playlist.save()
        print("playlist saved.")

    if echo:
        playlist.print()

    if not echo and not save and not token:
        if len(playlist.playlists) == 0:
            print("No playlists were generated. :(")
        elif len(playlist.playlists) == 1:
            print("A playlist with %d tracks was generated." % len(playlist.playlists[0].recordings))
        else:
            print("%d playlists were generated." % len(playlist.playlists))

        print("\nBut, you didn't tell me what to do with it, so I discarded it. (hint: use --token or --print)")

    sys.exit(0)


@cli.command(name="list")
def list_patches():
    """List all available patches"""
    patches = troi.utils.discover_patches()

    print("Available patches:")
    for slug in patches or []:
        print("  %s: %s" % (slug, patches[slug]().description()))


@cli.command()
@click.argument("patch", nargs=1)
def info(patch):
    """Get info for a given patch"""
    patches = troi.utils.discover_patches()
    if patch not in patches:
        print("Cannot load patch '%s'. Use the list command to get a list of available patches." % patch,
              file=sys.stderr)
        sys.exit(1)

    apatch = patches[patch]
    context = click.Context(apatch.parse_args, info_name=patch)
    click.echo(apatch.parse_args.get_help(context))


@cli.command(context_settings=dict(
    ignore_unknown_options=True,
))
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def test(args):
    """Run unit tests"""
    pytest.main(list(args))


if __name__ == "__main__":
    cli()
    sys.exit(0)
