import easydev
import os
import tempfile
import subprocess
import sys
from click.testing import CliRunner
from sequana_pipelines.ribofinder.main import main


from . import test_dir

sharedir = f"{test_dir}/data"

def test_standalone_subprocess():
    directory = tempfile.TemporaryDirectory()
    cmd = """sequana_ribofinder --input-directory {} 
            --working-directory {} --force""".format(sharedir, directory.name)
    subprocess.call(cmd.split())


def test_standalone_script():
    directory = tempfile.TemporaryDirectory()


    runner = CliRunner()
    results = runner.invoke(main, [ "--input-directory", sharedir, 
            "--working-directory", directory.name, "--force", "--rRNA-file", sharedir+"feature.fasta"])
    assert results.exit_code == 0


def test_full_rRNA_file():
    with tempfile.TemporaryDirectory() as directory:
        wk = directory
        cmd = f"sequana_ribofinder --input-directory {sharedir} "
        cmd += f"--working-directory {wk}  --force --rRNA-file {sharedir}/feature.fasta"
        subprocess.call(cmd.split())
        stat = subprocess.call("sh ribofinder.sh".split(), cwd=wk)
        assert os.path.exists(wk + "/summary.html")

def test_full_rRNA_extract():
    with tempfile.TemporaryDirectory() as directory:
        wk = directory
        cmd = f"sequana_ribofinder --input-directory {sharedir} "
        cmd += f"--working-directory {wk}  --force --reference-file {sharedir}/Lepto.fa --gff-file {sharedir}/Lepto.gff"
        subprocess.call(cmd.split())
        stat = subprocess.call("sh ribofinder.sh".split(), cwd=wk)


        if os.path.exists(wk + "/summary.html"):
            pass
        else:
            with open(f"{wk}/indexing/bowtie_rRNA.log", "r") as fout: 
                print(fout.read())
            raise IOError

def test_version():
    cmd = "sequana_ribofinder --version"
    subprocess.call(cmd.split())


