import csv
import os
from collections import defaultdict
from datetime import datetime
from io import StringIO
from typing import DefaultDict, List

import sys
import git
from binaryornot.check import is_binary
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
from git.remote import RemoteProgress
from loguru import logger

from utils import get_project_root, get_number_of_files


class Repository:
    """Class representing a repository (local/remote) to crawl, offers methods to parse blames/commits of a repository

    Attributes:
        repository_name: name of the repository (name of the folder)
        project-name: name of the project the repository belongs to, mainly used to create folders for commits/blames
        remote_url: remote url of the repository
        working_dir: local directory the repository is in
        repository: (see git.Repo)
        repository_git: (see git.Git)

    """

    BLAME_FIELDNAMES = ["sha", "line_number", "author",
                        "author-mail", "author-time", "author-tz",
                        "committer", "committer-mail", "committer-time", "committer-tz",
                        "summary", "file_path", "changed_line"]

    COMMIT_FIELDNAMES = ["filename", "insertions", "deletions", "lines", "author", "sha",
                         "authored_date_timestamp", "authored_date"]

    # quotation marks around {} to avoid errors with paths containing spaces, e.g. "C:/Users/My cool file.txt"
    BLAME_COMMAND = 'git blame -M -D --line-porcelain "{}"'

    def __str__(self) -> str:
        return f"Repository <remote_url:{self.remote_url}, working_dir: {self.working_dir}>"

    def __init__(self, remote_url: str, ssh_path: str = None, project_name: str = "",verbose=False) -> None:

        """Initializes Repository object

        The repository object holds information about the local directory as well as the remote of a repository.
        If

        Args:
            remote_url: URL of a remote repository i.e: ssh.github.om
            working_dir: local directory of the repository (working directory), i.e: ./repositories/

        Returns:

        """
        logger.remove()
        if verbose:
            logger.add(sys.stderr, format="{level: <8} | {message}", level="DEBUG")
        else:
            logger.add(sys.stderr, format="{level: <8} | {message}", level="INFO")
        # Check if complete URL is provided
        if not remote_url.endswith(".git"):
            raise InvalidGitRepositoryError("The URL doesn't seem valid. Please provide a valid url, e.g.: http://github.com/project/repo.git")

        self.repository_name = remote_url[(remote_url.rindex("/") + 1):remote_url.rindex(".git")]
        self.remote_url = remote_url
        self.path_prefix = project_name
        self.ssh_path = None
        self.progress_info = self.ProgressInfo()

        self.working_dir = os.path.join(get_project_root(), "temp", "repositories", self.path_prefix, self.repository_name)

        self.repository_git = git.Git(self.working_dir)
        if ssh_path is not None:
            self.ssh_path = str(ssh_path).replace("\\", "\\\\")
            self.repository_git.update_environment(GIT_SSH_COMMAND=f"ssh -i {self.ssh_path}")

        try:
            self.repository = git.Repo(self.working_dir)
        except InvalidGitRepositoryError:
            logger.info(
                f"{os.path.abspath(self.working_dir)} is not a valid git repository (no .git folder), clone {self.remote_url} into {os.path.abspath(self.working_dir)}")
            self.repository = self.__clone_from_remote()
        except NoSuchPathError:
            logger.info(
                f"{os.path.abspath(self.working_dir)} does not exist - trying to clone {self.remote_url} into {os.path.abspath(self.working_dir)}")
            self.repository = self.__clone_from_remote()

    @logger.catch(exception=GitCommandError)
    def __clone_from_remote(self) -> git.Repo:
        """Internal method to clone a remote repository

        Returns:
            Repository in self.remote_url pointing to self.working_dir

        """
        logger.info(f"Cloning {self.remote_url} to {self.working_dir}")
        if self.ssh_path is not None:
            cloned_repo = git.repo.base.Repo.clone_from(url=self.remote_url,
                                                        to_path=self.working_dir, progress=self.progress_info,
                                                        env={"GIT_SSH_COMMAND": f"ssh -i {self.ssh_path}"})
        else:
            cloned_repo = git.repo.base.Repo.clone_from(url=self.remote_url,
                                                        to_path=self.working_dir, progress=self.progress_info)
        logger.info(f"Successfully cloned repo {self.remote_url} into {os.path.abspath(self.working_dir)}")
        return cloned_repo


    @logger.catch
    def commits_to_file(self) -> None:
        """writes commits of a repository to a csv file

        :return: .csv file containing commits of repository located at  ./temp/files/commits/commits-{self.repository_name}.csv
        """
        out_file_path = os.path.join(get_project_root(), "files", "commits", self.path_prefix,
                                     f"commits-{self.repository_name}.csv")
        os.makedirs(os.path.dirname(out_file_path), exist_ok=True)
        with open(out_file_path, "w", newline="") as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=Repository.COMMIT_FIELDNAMES, quoting=csv.QUOTE_ALL)
            csv_writer.writeheader()
            for commit in self.repository.iter_commits():
                files_of_commit = [row for row in self._generate_commit_numstat_line(commit)]
                csv_writer.writerows(files_of_commit)

    @logger.catch
    def _generate_commit_numstat_line(self, commit: git.Repo.commit):
        """

        Args:
            commit: see git.Repo.commit

        Returns: A dict containing information about a single file of a commit (see git log --numstat)

        """
        for file_name, modifications in commit.stats.files.items():
            row = {
                "filename":                file_name,
                "insertions":              modifications["insertions"],
                "deletions":               modifications["deletions"],
                "lines":                   modifications["lines"],
                "author":                  commit.author.name,
                "sha":                     commit.hexsha,
                "authored_date":           datetime.fromtimestamp(commit.authored_date),
                "authored_date_timestamp": commit.authored_date,
            }
            # TODO lazy print dictionary und commit wenn level = debug
            yield row

    @logger.catch
    def blames_to_file(self) -> str:
        """writes blames of a repository to a csv file
                :return: csv-file containing commits of repository, either located at out_file_path
        """
        out_file_path = os.path.join(get_project_root(), "temp", "files", "blames", self.path_prefix,
                                     f"blames-{self.repository_name}.csv")
        os.makedirs(os.path.dirname(out_file_path), exist_ok=True)
        with open(out_file_path, "w", newline="", encoding="utf-8", errors="replace") as csv_file:
            csv_writer = csv.DictWriter(csv_file,
                                        fieldnames=Repository.BLAME_FIELDNAMES,
                                        quoting=csv.QUOTE_ALL,
                                        escapechar="\\")
            csv_writer.writeheader()
            for blame in self.__get_blames():
                for line in blame:
                    csv_writer.writerow(line)
        return out_file_path

    @logger.catch
    def __get_blames(self) -> None:
        """ traverses a repository and calls git blame on every occuring file

        Returns:
            A generator that generates git blame infos
        """
        number_of_files = get_number_of_files(self.working_dir)
        total_files, total_directories, parsed_files, skipped_files = 0, 0, 1, 0
        for dirpath, dirnames, filenames in os.walk(self.working_dir):
            for d in dirnames:
                if d[0] == ".":
                    dirnames.remove(d)
                    logger.debug("Skipped dot-folder {folder_name}", folder_name=d)

            for f in filenames:
                if f[0] == ".":
                    filenames.remove(f)
                    logger.debug("Skipped dot-file {file_name}", file_name=f)
                    skipped_files += 1
                    parsed_files += 1
            total_directories = len(dirnames)
            logger.info("Parsing files of {dirpath}",dirpath=dirpath)
            for filename in filenames:
                relative_file_path = os.path.relpath(os.path.join(dirpath, filename), self.working_dir)
                if is_binary(os.path.join(dirpath, filename)):
                    logger.debug("Progress {parsed_files}/{total_files} - Skipped parsing blames of file {path}",
                                 parsed_files=parsed_files, total_files=number_of_files, path=relative_file_path)
                    skipped_files += 1

                else:
                    logger.debug("Progress {parsed_files}/{total_files} - parsing blames of file {path}",
                                 path=relative_file_path, parsed_files=parsed_files, total_files=number_of_files)
                    yield self._get_blame(relative_file_path)
                parsed_files += 1
        logger.info(
            "Finished parsing blames of {repo} - {parsed_files} files({skipped_files} skipped) in {total_directories} directories.",
            repo=self.repository_name, parsed_files=parsed_files, skipped_files=skipped_files,
            total_directories=total_directories)

    @logger.catch
    def _get_blame(self, relative_file_path):
        """single git blame call on a file

        Args:
            relative_file_path:

        Returns:
            list of dictionaries containing blame info on a single file
        """

        blame_raw_output = StringIO(self.repository_git.execute(Repository.BLAME_COMMAND.format(relative_file_path)))
        blame_infos = []
        blame_header = []
        for line in blame_raw_output.readlines():
            blame_header.append(line.strip())
            if not line.startswith("\t"):
                pass
            else:
                blame_infos.append(self._parse_blame(blame_header, relative_file_path))
                blame_header = []
        return blame_infos

    @logger.catch
    def _parse_blame(self, blame_header: List[str], file_path: str) -> DefaultDict[str, str]:
        """parses output of git blame --line-porcelain into a dictionary

        Args:
            blame_header: content of the header lines output of "git blame --line-porcelain"
            file_path: file-path (added in the resulting dictionary as key "file_path")

        Returns:
            a dictionary containing information about a single blame line
        """
        blame_info = defaultdict(lambda x: "null")
        line_with_sha = blame_header[0].split(" ")
        blame_info["sha"] = line_with_sha[0]
        blame_info["line_number"] = line_with_sha[2]
        blame_info["file_path"] = file_path
        for entry in blame_header[1:-1]:
            if entry.startswith("boundary"):
                continue
            key, value = entry.split(" ", 1)
            blame_info[key] = value
        # TODO: drop all keys not present in field_names
        blame_info.pop("previous", "")
        blame_info.pop("filename", "")
        # TODO: log result of parsing lazily for debug
        return blame_info

    class ProgressInfo(RemoteProgress):
        def update(self, op_code, cur_count, max_count=None, message=''):
            pass
            # print(self._cur_line)