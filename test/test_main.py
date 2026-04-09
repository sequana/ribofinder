import os
import subprocess
import tempfile

import pytest
from click.testing import CliRunner

from sequana_pipelines.ribofinder.main import main

from . import test_dir

sharedir = f"{test_dir}/data"


# -----------------------------------------------------------------------------
# Setup-only tests (no snakemake execution). Fast and safe to run on any host
# because they don't need bowtie2/bwa/samtools to be available on PATH.
# -----------------------------------------------------------------------------


def test_standalone_subprocess():
    with tempfile.TemporaryDirectory() as directory:
        cmd = f"sequana_ribofinder --input-directory {sharedir} "
        cmd += f"--working-directory {directory} --force "
        cmd += f"--rRNA-file {sharedir}/feature.fasta"
        subprocess.call(cmd.split())


def test_standalone_script():
    with tempfile.TemporaryDirectory() as directory:
        runner = CliRunner()
        results = runner.invoke(
            main,
            [
                "--input-directory", sharedir,
                "--working-directory", directory,
                "--force",
                "--rRNA-file", f"{sharedir}/feature.fasta",
            ],
        )
        assert results.exit_code == 0


def test_standalone_script_bowtie2_explicit():
    """Explicit --aligner bowtie2 should write bowtie2 in the generated config."""
    with tempfile.TemporaryDirectory() as directory:
        runner = CliRunner()
        results = runner.invoke(
            main,
            [
                "--input-directory", sharedir,
                "--working-directory", directory,
                "--force",
                "--rRNA-file", f"{sharedir}/feature.fasta",
                "--aligner", "bowtie2",
            ],
        )
        assert results.exit_code == 0
        with open(os.path.join(directory, "config.yaml")) as fin:
            content = fin.read()
        assert "aligner: bowtie2" in content
        # multiqc module should auto-track the aligner selection
        assert "modules: bowtie2" in content


def test_standalone_script_bwa():
    """--aligner bwa must switch both the aligner and the multiqc modules."""
    with tempfile.TemporaryDirectory() as directory:
        runner = CliRunner()
        results = runner.invoke(
            main,
            [
                "--input-directory", sharedir,
                "--working-directory", directory,
                "--force",
                "--rRNA-file", f"{sharedir}/feature.fasta",
                "--aligner", "bwa",
            ],
        )
        assert results.exit_code == 0
        with open(os.path.join(directory, "config.yaml")) as fin:
            content = fin.read()
        assert "aligner: bwa" in content
        assert "modules: samtools" in content


def test_standalone_script_invalid_aligner():
    """click should reject any aligner outside the declared choice."""
    with tempfile.TemporaryDirectory() as directory:
        runner = CliRunner()
        results = runner.invoke(
            main,
            [
                "--input-directory", sharedir,
                "--working-directory", directory,
                "--force",
                "--rRNA-file", f"{sharedir}/feature.fasta",
                "--aligner", "bowtie1",
            ],
        )
        assert results.exit_code != 0


def test_standalone_script_gff():
    """Setup pipeline from reference fasta + GFF annotation."""
    with tempfile.TemporaryDirectory() as directory:
        runner = CliRunner()
        results = runner.invoke(
            main,
            [
                "--input-directory", sharedir,
                "--working-directory", directory,
                "--force",
                "--reference-file", f"{sharedir}/Lepto.fa",
                "--gff-file", f"{sharedir}/Lepto.gff",
            ],
        )
        assert results.exit_code == 0


def test_standalone_script_missing_inputs():
    """Neither --rRNA-file nor --reference-file should fail with a clear exit."""
    with tempfile.TemporaryDirectory() as directory:
        runner = CliRunner()
        results = runner.invoke(
            main,
            [
                "--input-directory", sharedir,
                "--working-directory", directory,
                "--force",
            ],
        )
        assert results.exit_code != 0


def test_version():
    cmd = "sequana_ribofinder --version"
    subprocess.call(cmd.split())


# -----------------------------------------------------------------------------
# End-to-end pipeline tests. These require bowtie2 / bwa / samtools / sambamba
# / bedtools / pigz to be available on PATH (CI provides them via
# environment.yml).
# -----------------------------------------------------------------------------


def _assert_pipeline_outputs(wk):
    """Shared post-run assertions for end-to-end tests."""
    assert os.path.exists(os.path.join(wk, "summary.html")), "summary.html missing"
    assert os.path.exists(os.path.join(wk, "outputs/proportions.png"))
    assert os.path.exists(os.path.join(wk, "outputs/RPKM.png"))
    assert os.path.exists(os.path.join(wk, "multiqc/multiqc_report.html"))
    # New explanatory sections from v1.2.0 must be embedded in the summary.
    with open(os.path.join(wk, "summary.html")) as fin:
        html = fin.read()
    assert "How it works" in html
    assert "Per-sequence distribution of ribosomal hits" in html
    assert "Per-sequence RPKM distribution" in html


def test_full_rRNA_file():
    """Default aligner (bowtie2) + pre-built rRNA fasta."""
    with tempfile.TemporaryDirectory() as wk:
        cmd = f"sequana_ribofinder --input-directory {sharedir} "
        cmd += f"--working-directory {wk}  --force --rRNA-file {sharedir}/feature.fasta"
        subprocess.call(cmd.split())
        rc = subprocess.call("bash ribofinder.sh".split(), cwd=wk)
        assert rc == 0
        _assert_pipeline_outputs(wk)
        # bowtie2 mapper directory should exist for each sample
        assert os.path.isdir(os.path.join(wk, "data/bowtie2"))


def test_full_rRNA_extract():
    """Default aligner (bowtie2) + on-the-fly rRNA extraction from GFF."""
    with tempfile.TemporaryDirectory() as wk:
        cmd = f"sequana_ribofinder --input-directory {sharedir} "
        cmd += (
            f"--working-directory {wk}  --force "
            f"--reference-file {sharedir}/Lepto.fa --gff-file {sharedir}/Lepto.gff"
        )
        subprocess.call(cmd.split())
        rc = subprocess.call("bash ribofinder.sh".split(), cwd=wk)
        if rc != 0:
            log = os.path.join(wk, "indexing/bowtie2_rRNA.log")
            if os.path.exists(log):
                with open(log) as fout:
                    print(fout.read())
            raise IOError("pipeline failed")
        _assert_pipeline_outputs(wk)


def test_full_bwa():
    """--aligner bwa must produce the same set of outputs as the bowtie2 run."""
    with tempfile.TemporaryDirectory() as wk:
        cmd = f"sequana_ribofinder --input-directory {sharedir} "
        cmd += (
            f"--working-directory {wk}  --force "
            f"--rRNA-file {sharedir}/feature.fasta --aligner bwa"
        )
        subprocess.call(cmd.split())
        rc = subprocess.call("bash ribofinder.sh".split(), cwd=wk)
        assert rc == 0
        _assert_pipeline_outputs(wk)
        # bwa-specific outputs: per-sample sorted BAM and samtools stats file.
        assert os.path.isdir(os.path.join(wk, "data/bwa"))
        assert os.path.exists(
            os.path.join(wk, "data/samtools_stats/data.stats.txt")
        )
        # multiqc should pick up samtools-stats data when aligner == bwa.
        assert os.path.exists(
            os.path.join(wk, "multiqc/multiqc_data/multiqc_samtools_stats.txt")
        )


def test_full_bwa_extract():
    """--aligner bwa combined with reference+gff extraction."""
    with tempfile.TemporaryDirectory() as wk:
        cmd = f"sequana_ribofinder --input-directory {sharedir} "
        cmd += (
            f"--working-directory {wk}  --force "
            f"--reference-file {sharedir}/Lepto.fa "
            f"--gff-file {sharedir}/Lepto.gff --aligner bwa"
        )
        subprocess.call(cmd.split())
        rc = subprocess.call("bash ribofinder.sh".split(), cwd=wk)
        assert rc == 0
        _assert_pipeline_outputs(wk)
