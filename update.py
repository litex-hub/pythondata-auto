#!/usr/bin/env python3

import os
import configparser
import pprint
import subprocess
import sys

import github


MAX_ATTEMPTS = 3
GIT_MODE="git+ssh"

def github_repo_config(module_data):
    config = dict(
        has_issues=False,
        has_wiki=False,
        has_downloads=False,
        has_projects=False,
    )
    config['description'] = """
Python module containing data files for using {n} with LiteX.
""".format(n=module_data['human_name']).strip()
    config['homepage'] = module_data['src']
    return config


def github_repo_create(g, module_data):
    org = g.get_organization('litex-hub')
    org.create_repo(module_data['repo'], **github_repo_config(module_data))


def github_repo(g, module_data):
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        attempts += 1
        try:
            repo = g.get_repo('litex-hub/'+module_data['repo'])
            repo.edit(**github_repo_config(module_data))
            print(repo)
            break
        except github.UnknownObjectException as e:
            print(e)
            github_repo_create(g, module_data)


def download(module_data):
    out_path = os.path.join('repos',module_data['repo'])
    if not os.path.exists(out_path):
        subprocess.check_call(
            ["git", "clone", module_data['repo_url'], out_path])
    else:
        subprocess.check_call(["git", "pull"], pwd=out_path)


def main(name, argv):
    token = os.environ.get('GITHUB_API_TOKEN', None)
    if token:
        g = github.Github(token)
    else:
        g = github.Github()

    config = configparser.ConfigParser()
    config.read('modules.ini')
    for module in config.sections():
        repo_name = 'litex-data-{t}-{mod}'.format(
            t=config[module]['type'],
            mod=module)
        config[module]['repo'] = repo_name
        config[module]['repo_url'] = "{mode}://github.com/litex-hub/{repo}.git".format(
            mode=GIT_MODE,
            repo=repo_name)
        print()
        print(module)
        pprint.pprint(list(config[module].items()))
        github_repo(g, config[module])



    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[0], sys.argv[1:]))
