#
#  This file is part of Sequana software
#
#  Copyright (c) 2016 - Sequana Development Team
#
#  Distributed under the terms of the 3-clause BSD license.
#  The full license is in the LICENSE file, distributed with this software.
#
#  website: https://github.com/sequana/sequana
#  documentation: http://sequana.readthedocs.io
#
##############################################################################
import sys
import os
import subprocess
import shutil
from pathlib import Path

import rich_click as click
import click_completion

click_completion.init()

from sequana_pipetools.options import *
from sequana_pipetools import SequanaManager


NAME = "ribofinder"

help = init_click(
    NAME,
    groups={
        "Pipeline Specific": [
            "--aligner",
            "--genbank-file",
            "--gff-file",
            "--rRNA-feature",
            "--rRNA-file",
            "--reference-file",
        ],
    },
)


@click.command(context_settings=help)
@include_options_from(ClickSnakemakeOptions, working_directory=NAME)
@include_options_from(ClickSlurmOptions)
@include_options_from(ClickInputOptions)
@include_options_from(ClickGeneralOptions)
@click.option(
    "--aligner", "aligner", type=click.Choice(["bowtie1"]), default="bowtie1", help="the alignement tool (bowtie1)"
)
@click.option(
    "--rRNA-feature",
    "rRNA_feature",
    default="rRNA",
    type=click.STRING,
    help="""Feature name corresponding to the rRNA to be identified for QCs""",
)
@click.option(
    "--rRNA-file",
    "rRNA_file",
    default=None,
    type=click.Path(file_okay=True, dir_okay=False),
    help="""If you already have the rRNA file, just provide it""",
)
@click.option("--genbank-file", default=None, help="""genbank. if provided, do not provide gff""")
@click.option("--gff-file", default=None, help="""If provided, do not provide genbank""")
@click.option("--reference-file", default=None, help="""The required referenceto fetch features into""")
def main(**options):
    # the real stuff is here
    manager = SequanaManager(options, NAME)

    # create the beginning of the command and the working directory
    manager.setup()

    # aliases
    options = manager.options
    cfg = manager.config.config

    # fills input_data, input_directory, input_readtag
    # needs an update of sequana_pipetools to exclude readtag
    manager.fill_data_options()

    # fill the config file with input parameters

    # --------------------------------------------------------- general
    def fill_aligner():
        cfg.general.aligner = options.aligner

    def fill_rRNA_feature():
        cfg.general.rRNA_feature = options.rRNA_feature

    def fill_rRNA_file():
        if options.rRNA_file:
            cfg.general.rRNA_file = os.path.abspath(options.rRNA_file)

    def fill_genbank_file():
        if options.genbank_file:
            cfg.general.genbank_file = os.path.abspath(options.genbank_file)

    def fill_gff_file():
        if options.gff_file:
            cfg.general.gff_file = os.path.abspath(options.gff_file)

    def fill_reference_file():
        if options.reference_file:
            cfg.general.reference_file = os.path.abspath(options.reference_file)

    if options["from_project"]:
        if "--aligner" in sys.argv:
            fill_aligner()
        if "--rRNA-feature" in sys.argv:
            fill_rRNA_feature()
        if "--rRNA-file" in sys.argv:
            fill_rRNA_file()
        if "--genbank-file" in sys.argv:
            fill_genbank_file()
        if "--gff-file" in sys.argv:
            fill_gff_file()
        if "--reference-fle" in sys.argv:
            fill_reference_file()

    else:
        fill_aligner()
        fill_rRNA_feature()
        fill_rRNA_file()
        fill_genbank_file()
        fill_gff_file()
        fill_reference_file()

        if options.reference_file is None and options.rRNA_file is None:
            click.echo("You must provide a rRNA file or a reference_file", err=True)
            sys.exit(1)

        if options.reference_file:
            click.echo("checking your input GFF file and rRNA feature if provided")
            if options.genbank_file:
                from sequana.genbank import GenBank

                gbk = GenBank(options.genbank_file)
            if options.genbank_file is None and options.gff_file is None:
                click.echo("Most probably you want to provide an annotation (genbank-file or gff-file)", err=True)
                sys.exit(0)

    # finalise the command and save it; copy the snakemake. update the config
    # file and save it.
    manager.teardown()


if __name__ == "__main__":
    main()
