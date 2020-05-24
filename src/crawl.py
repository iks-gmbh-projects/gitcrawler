import argparse

import repository
from utils import convert_to_flare

parser = argparse.ArgumentParser(
    description="CLI Application to generate flare.json to be used in a packed circle visualization from a given repository")

parser.add_argument("remote_url", help="remote url of a git repository, e.g. https://github.com/sample/sample.git")
parser.add_argument("-v", "--verbose", help="shows debug messages , e.g. information on parsed files",
                    action="store_true")
args = parser.parse_args()

repo = repository.Repository(remote_url=args.remote_url, verbose=args.verbose)
out_file = repo.blames_to_file()
convert_to_flare(out_file)
