#!/usr/bin/env python3

import os
import configparser
import pprint
import subprocess
import sys
import shutil

import jinja2
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

    download(module_data)
    update(module_data)


def download(module_data):
    out_path = os.path.join('repos',module_data['repo'])
    if not os.path.exists(out_path):
        subprocess.check_call(
            ["git", "clone", module_data['repo_url'], out_path])
    else:
        subprocess.check_call(["git", "pull"], pwd=out_path)


def render(module_data, in_file, out_file):
    template = jinja2.Template(open(in_file).read())
    with open(out_file, 'w') as of:
        of.write(template.render(**module_data))


def os_path_split_all(x):
    """
    >>> os_path_split_all('/a/b/c/d')
    ['a', 'b', 'c', 'd']
    >>> os_path_split_all('a/b/c/d')
    ['a', 'b', 'c', 'd']

    >>> os_path_split_all('/a/b/c/')
    ['a', 'b', 'c']

    >>> os_path_split_all('a/b/c/')
    ['a', 'b', 'c']

    >>> os_path_split_all('/a/b/../')
    ['a']
    >>> os_path_split_all('a/b/../')
    ['a']

    >>> os_path_split_all('/a/b/./')
    ['a', 'b']
    >>> os_path_split_all('a/b/./')
    ['a', 'b']
    """
    x = os.path.normpath(x)
    bits = []
    a = x
    while a and a != '/':
        a, b = os.path.split(a)
        bits.insert(0, b)
    return bits


def repo_path(module_data, path, template_dir=os.path.abspath("templates")):
    """
    >>> repo_path({'repo': 'r'}, 't/a', 't')
    'repos/r/a'
    >>> repo_path({'repo': 'r'}, 't/a/b', 't')
    'repos/r/a/b'
    >>> repo_path({'repo': 'r', 'a': 'c'}, 't/__a__/b', 't')
    'repos/r/c/b'
    """
    template_path = os.path.normpath(os.path.relpath(path, template_dir))

    repo_bits = []
    template_bits = os_path_split_all(template_path)
    for b in template_bits:
        if not b.endswith('__'):
            repo_bits.append(b)
            continue
        assert b.startswith('__'), b
        d = b[2:-2]
        repo_bits.append(module_data[b[2:-2]])

    repo_dir = os.path.join('repos', module_data['repo'])
    return os.path.normpath(os.path.join(repo_dir, *repo_bits))


def git_add_file(module_data, f):
    repo_dir = os.path.abspath(os.path.join('repos', module_data['repo']))
    cmd = ['git', 'add', os.path.relpath(f, repo_dir)]
    print("In", repo_dir, repr(" ".join(cmd)))
    subprocess.check_call(cmd, cwd=repo_dir)


def u(n, dst, src):
    print("{:>10s} {:60s} from {}".format(n, dst, src))


def update(module_data):
    print()
    print("Updating:", module_data['repo'])
    print('-'*75)
    repo_dir = os.path.abspath(os.path.join('repos', module_data['repo']))

    top_dir = os.path.abspath('.')
    template_dir = os.path.abspath(os.path.join(top_dir, "templates"))
    for root, dirs, files in os.walk(template_dir, topdown=True):
        path = os.path.join(template_dir, root)
        repo_root = repo_path(module_data, path, template_dir)
        u("Updating", repo_root, root)
        if not os.path.exists(repo_root):
            os.makedirs(repo_root)

        for d in dirs:
            path_d = os.path.join(path, d)
            repo_d = repo_path(module_data, path_d, template_dir)
            u("Creating", repo_d, path_d)
            if not os.path.exists(repo_d):
                os.makedirs(repo_d)

        for f in files:
            path_f = os.path.join(path, f)
            repo_f = repo_path(module_data, path_f, template_dir)

            fbase, ext = os.path.splitext(f)
            if ext in ('.swp', '.swo'):
                continue

            if ext in ('.jinja',):
                repo_f = repo_f[:-6]
                u("Rendering", repo_f, path_f)
                render(module_data, path_f, repo_f)
            else:
                u("Copying", repo_f, path_f)
                shutil.copy(path_f, repo_f)
            #git_add_file(module_data, repo_f)
    print('-'*75)



def main(name, argv):
    token = os.environ.get('GITHUB_API_TOKEN', None)
    if token:
        g = github.Github(token)
    else:
        g = github.Github()

    config = configparser.ConfigParser()
    config.read('modules.ini')
    for module in config.sections():
        m = config[module]

        repo_name = 'litex-data-{t}-{mod}'.format(
            t=m['type'],
            mod=module)
        m['name'] = module
        m['repo'] = repo_name
        m['repo_url'] = "{mode}://github.com/litex-hub/{repo}.git".format(
            mode=GIT_MODE,
            repo=repo_name)
        m['repo_https'] = "https://github.com/litex-hub/{repo}.git".format(
            repo=repo_name)
        m['py'] = 'litex.{type}.{name}'.format(type=m['type'], name=module)
        m['dir'] = os.path.join('litex', m['type'], module, m['contents'])
        print()
        print(module)
        pprint.pprint(list(m.items()))
        #github_repo(g, m)
        update(m)
        break



    return 0


if __name__ == "__main__":
    import doctest
    doctest.testmod()
    sys.exit(main(sys.argv[0], sys.argv[1:]))
