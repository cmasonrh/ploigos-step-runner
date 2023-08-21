"""Shared utils for git operations.

NOTE: There is heavy overlap between this class and `GitMixin`. An architectural decision needs
      to be made on composition vs. multiple inheritance for gaining consistency between unrelated
      step implementers that require the same configuration parameters / behaviors.
"""


import re
import sh
import sys

from collections import OrderedDict
from datetime import datetime
from io import StringIO
from ploigos_step_runner.utils.io import \
    create_sh_redirect_to_multiple_streams_fn_callback
from ploigos_step_runner.exceptions import StepRunnerException

GIT_REPO_REGEX = re.compile(r"(?P<protocol>^https:\/\/|^http:\/\/)?(?P<address>.*$)")

def get_git_auth_url( #pylint: dsable=too-many-arguments
    repo_url,
    username=None,
    password=None       
):
    """Generate the git url with supplied authentication.

    Parameters
    ----------
    repo_url : str
        URI of the repository.
    username : str
        Username for the remote git repo (if required)
    password : str
        Password for the remote git repo (if required)

    Returns
    -------
    str
        Authitcation url for git repository.
    """

    repo_match = get_git_repo_regex().match(repo_url)
    repo_protocol = repo_match.groupdict()['protocol']
    repo_address = repo_match.groupdict()['address']

    # if deployment config repo uses http/https push using user/pass
    # else push using ssh
    if username and password and repo_protocol and re.match(
            r'^http://|^https://',
            repo_protocol
    ):
        repo_url_with_auth = \
            f"{repo_protocol}{username}:{password}" \
            f"@{repo_address}"
    else:
        repo_url_with_auth = repo_url

    return repo_url_with_auth


def clone_repo(  # pylint: disable=too-many-arguments
    repo_dir,
    repo_url,
    username=None,
    password=None
):
    """Clones the repository specified in repo_url.

    Parameters
    ----------
    repo_dir : str
        Path to where to clone the repository
    repo_url : str
        URI of the repository to clone.
    username : str
        Username for the remote git repo (if required)
    password : str
        Password for the remote git repo (if required)

    Raises
    ------
    StepRunnerException
    * if error cloning repository
    """
    repo_match = get_git_repo_regex().match(repo_url)
    repo_protocol = repo_match.groupdict()['protocol']
    repo_address = repo_match.groupdict()['address']

    # if deployment config repo uses http/https push using user/pass
    # else push using ssh
    if username and password and repo_protocol and re.match(
            r'^http://|^https://',
            repo_protocol
    ):
        repo_url_with_auth = \
            f"{repo_protocol}{username}:{password}" \
            f"@{repo_address}"
    else:
        repo_url_with_auth = repo_url

    try:
        sh.git.clone(  # pylint: disable=no-member
            repo_url_with_auth,
            repo_dir,
            _out=sys.stdout,
            _err=sys.stderr
        )
    except sh.ErrorReturnCode as error:
        raise StepRunnerException(
            f"Error cloning repository ({repo_url}): {error}"
        ) from error

def git_config(  # pylint: disable=too-many-arguments
    repo_dir,
    git_email,
    git_name
):
    """Sets the git config (username + email) for the git repository residing under repo_dir.

    Parameters
    ----------
    repo_dir : str
        Path to where to clone the repository
    git_email : str
        email to use when performing git operations in the cloned repository
    git_name : str
        name to use when performing git operations in the cloned repository

    Raises
    ------
    StepRunnerException
    * if error configuring repo user
    """

    try:
        sh.git.config(  # pylint: disable=no-member
            'user.email',
            git_email,
            _cwd=repo_dir,
            _out=sys.stdout,
            _err=sys.stderr
        )
        sh.git.config(  # pylint: disable=no-member
            'user.name',
            git_name,
            _cwd=repo_dir,
            _out=sys.stdout,
            _err=sys.stderr
        )
    except sh.ErrorReturnCode as error:
        # NOTE: this should never happen
        raise StepRunnerException(
            f"Unexpected error configuring git user.email ({git_email})"
            f" and user.name ({git_name}) for repository"
            f" under directory ({repo_dir}): {error}"
        ) from error

def git_checkout(
    repo_dir,
    repo_branch
):
    """Checks out a specifc branch in the given git repository.

    Parameters
    ----------
    repo_dir : str
        Path to an existing git repository
    repo_branch : str
        The branch to checkout.

    Raises
    ------
    StepRunnerException
    * if error checking out branch of repository
    """
    try:
        # no atomic way in git to checkout out new or existing branch,
        # so first try to check out existing, if that doesn't work try new
        try:
            sh.git.checkout(  # pylint: disable=no-member
                repo_branch,
                _cwd=repo_dir,
                _out=sys.stdout,
                _err=sys.stderr
            )
        except sh.ErrorReturnCode:
            sh.git.checkout(
                '-b',
                repo_branch,
                _cwd=repo_dir,
                _out=sys.stdout,
                _err=sys.stderr
            )
    except sh.ErrorReturnCode as error:
        # NOTE: this should never happen
        raise StepRunnerException(
            f"Unexpected error checking out new or existing branch ({repo_branch})"
            f" from repository under directory ({repo_dir}): {error}"
        ) from error

def git_commit_file(
    git_commit_message,
    file_path,
    repo_dir
):
    """Adds and commits a file.
    NOTE: In the future, this should be split between two methods, to allow adding multiple files
          before committing.

    Parameters
    ----------
    git_commit_message : str
        The message to apply on commit.
    file_path : str
        The file to commit.
    repo_dir : str
        Path to an existing git repository.

    Raises
    ------
    StepRunnerException
    * if error adding or committing the file
    """
    try:
        sh.git.add( # pylint: disable=no-member
            file_path,
            _cwd=repo_dir,
            _out=sys.stdout,
            _err=sys.stderr
        )
    except sh.ErrorReturnCode as error:
        # NOTE: this should never happen
        raise StepRunnerException(
            f"Unexpected error adding file ({file_path}) to commit"
            f" in git repository ({repo_dir}): {error}"
        ) from error

    try:
        sh.git.commit( # pylint: disable=no-member
            '--allow-empty',
            '--all',
            '--message', git_commit_message,
            _cwd=repo_dir,
            _out=sys.stdout,
            _err=sys.stderr
        )
    except sh.ErrorReturnCode as error:
        # NOTE: this should never happen
        raise StepRunnerException(
            f"Unexpected error commiting file ({file_path})"
            f" in git repository ({repo_dir}): {error}"
        ) from error

def git_update_ref_and_push(
    repo_dir,
    git_ref_root,
    git_ref,
    git_ref_value,
    url=None,
    force_push_ref=False,
):
    """Create a git reference.

    Parameters
    ----------
    repo_dir : str
        Path to an existing git repository.
    git_ref_root : str
        Value of the reference root. Should begin with refs/
    git_ref : str
        Name of the reference to create in the root. 
    git_ref_value : str
        Value to create a Git reference with with. Can be another ref or hash.
    url : str, default None
        URI of git repo, if different than origin under repo_dir.
    force_push_ref : bool, default False
        If the reference should be created even if one already exists.

    Raises
    ------
    StepRunnerException
        If given git reference is not valid as determined by 'git check-ref-format'.
        If given git reference already exists.
        If error creating Git update-ref.
    """
    git_ref_full = git_ref_root + git_ref
    try:
        #Check the ref format is valid
        try:
            sh.git(
                "check-ref-format",
                git_ref_full,
                _out=sys.stdout,
                _err=sys.stderr
            )
        except sh.ErrorReturnCode_1:
            raise Exception(
                f"Reference ({git_ref_full}) has improper format."
            )
        
        #Update or create a new reference
        if force_push_ref:
            sh.git(
                "update-ref",
                git_ref_full,
                git_ref_value, 
                _cwd=repo_dir,
                _out=sys.stdout,
                _err=sys.stderr
            )
        else:
            remote = url if url else 'origin'
            try:
                sh.git(
                    "fetch",
                    "--refmap=''",
                    remote,
                    git_ref_full + ':' + git_ref_full,
                    _cwd=repo_dir,
                    _out=sys.stdout,
                    _err=sys.stderr
                )
            except (Exception) as error:
                if repr(error).find("Couldn't find remote ref") != -1:
                    raise Exception(
                        f"Reference ({git_ref_full}) already exists in remote."
                    )

            sh.git(
                "update-ref",
                git_ref_full,
                git_ref_value, 
                '',
                _cwd=repo_dir,
                _out=sys.stdout,
                _err=sys.stderr
            )

        #Push the new reference
        git_push = sh.git.push.bake(url) if url else sh.git.push.bake('origin')
        git_push(
            git_ref_full + ':' + git_ref_full,
            _cwd=repo_dir,
            _out=sys.stdout,
            _err=sys.stderr
        )

    except (Exception) as error:
        raise StepRunnerException(
            f"Error creating git reference ({git_ref_full}) for ({git_ref_value}): {error}"
        ) from error

def git_tag_and_push(
    repo_dir,
    tag,
    url=None,
    force_push_tags=False
):
    """Tags a commit and pushes it.
    NOTE: In the future, this should be split between two methods, to allow additional actions
          after tagging without requiring multiple pushes.

    Parameters
    ----------
    repo_dir : str
        Path to an existing git repository.
    tag : str
        Tag (label) to apply.
    url : str
        URI of git repo, if different than the default as configured under repo_dir.
    force_push_tags : bool
        Whether to force push when history between the local and remote branch differs.

    Raises
    ------
    StepRunnerException
    * if error pushing commits
    * if error tagging repository
    * if error pushing tags
    """

    git_push = sh.git.push.bake(url) if url else sh.git.push

    # push commits
    try:
        git_push(
            _cwd=repo_dir,
            _out=sys.stdout
        )
    except sh.ErrorReturnCode as error:
        raise StepRunnerException(
            f"Error pushing commits from repository directory ({repo_dir}) to"
            f" repository ({url}): {error}"
        ) from error

    # tag
    try:
        # NOTE:
        # this force is only needed locally in case of a re-run of the same pipeline
        # without a fresh check out. You will notice there is no force on the push
        # making this an acceptable work around to the issue since on the off chance
        # actually overwriting a tag with a different comment, the push will fail
        # because the tag will be attached to a different git hash.
        sh.git.tag(  # pylint: disable=no-member
            tag,
            '-f',
            _cwd=repo_dir,
            _out=sys.stdout,
            _err=sys.stderr
        )
    except sh.ErrorReturnCode as error:
        raise StepRunnerException(
            f"Error tagging repository ({repo_dir}) with tag ({tag}): {error}"
        ) from error

    git_push_additional_arguments = []
    if force_push_tags:
        git_push_additional_arguments += ["--force"]

    # push tag
    try:
        git_push(
            '--tag',
            *git_push_additional_arguments,
            _cwd=repo_dir,
            _out=sys.stdout
        )
    except sh.ErrorReturnCode as error:
        raise StepRunnerException(
            f"Error pushing tags from repository directory ({repo_dir}) to"
            f" repository ({url}): {error}"
        ) from error

def get_git_repo_regex():
    """Getter for the StepImplementer's configuration defaults.

    Returns
    -------
    str
        The regex representing a valid git repo URI.
    """
    return GIT_REPO_REGEX

def git_orderd_tag_refs_with_created(
    repo_dir,
    url=None,
):
    """Create a git reference.

    Parameters
    ----------
    repo_dir : str
        Path to an existing git repository.
    url : str, default None
        URI of git repo, if different than origin under repo_dir.

    Returns
    -------
    dict :
        Orderd list of tag references and create dates

    Raises
    ------
    StepRunnerException
        If repo at url is not found.
    """
    try:
        remote = url if url else 'origin'
        sh.git(
            'fetch',
            '--tags',
            remote,
            _cwd=repo_dir,
            _out=sys.stdout,
            _err=sys.stderr
        )
        foreach_out_buff = StringIO()
        foreach_out_callback = create_sh_redirect_to_multiple_streams_fn_callback([
            sys.stdout,
            foreach_out_buff
        ])
        output = sh.git(
            'for-each-ref',
            '--sort=creatordate',
            '--format="%(creatordate)|%(refname)"',
            'refs/tags/',
            _cwd=repo_dir,
            _out=foreach_out_callback,
            _err=sys.stderr
        )
        tag_dict = OrderedDict()
        for line in foreach_out_buff.getvalue().splitlines():
            split_line = re.split('|', line)
            tag_dict[split_line[0]] = datetime.strptime(split_line[1],'%a %b %d %H:%M:%S %Y %z')
        for key, value in tag_dict.items():
            print(f'Ref:{key} Date:{value.strftime("%Y-%m-%d %H:%M:%S")}\n')

    except (Exception) as error:
        raise StepRunnerException(
            f"Error accessing repo: {error}"
        ) from error