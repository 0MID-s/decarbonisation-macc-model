"""Same bytes on every build and every PYTHONHASHSEED (SET-02, D-16).

Determinism is per platform/zlib build, not across operating systems.
"""
import hashlib
import os
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Plan 01-07 adds ("spike", "fixtures").
TARGET_DATASETS = sorted([("main", "config"), ("main", "fixtures")])
SEEDS = ("0", "1", "12345", None)


def build_file(target, dataset, seed, out):
    import subprocess
    env = dict(os.environ)
    if seed is None:
        env.pop("PYTHONHASHSEED", None)
    else:
        env["PYTHONHASHSEED"] = seed
    subprocess.run([sys.executable, "build.py", "--target", target,
                    "--dataset", dataset, "--out", out],
                   cwd=ROOT, env=env, check=True, capture_output=True)
    with open(out, "rb") as fh:
        return fh.read()


def crcs(data):
    import io
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return dict((i.filename, i.CRC) for i in z.infolist())


class Determinism(unittest.TestCase):
    def test_identical_across_seeds(self):
        for target, dataset in TARGET_DATASETS:
            with tempfile.TemporaryDirectory() as tmp:
                blobs = [build_file(target, dataset, seed,
                                    os.path.join(tmp, "o%d.xlsx" % i))
                         for i, seed in enumerate(SEEDS)]
            hashes = set(hashlib.sha256(b).hexdigest() for b in blobs)
            if len(hashes) != 1:
                base = crcs(blobs[0])
                diff = sorted(set(n for b in blobs[1:]
                                  for n, c in crcs(b).items() if base.get(n) != c))
                self.fail("%s/%s differs across seeds; members: %s"
                          % (target, dataset, diff))


if __name__ == "__main__":
    unittest.main()
