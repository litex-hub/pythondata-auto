#!/usr/bin/env python3

import configparser
import os
import pprint
import shutil
import subprocess
import sys
import tempfile

from collections import OrderedDict
from packaging import version

import jinja2
import github


MAX_ATTEMPTS = 3
GIT_MODE=os.environ.get('GIT_MODE', "git+ssh")

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
    if 'src' in module_data:
        config['homepage'] = module_data['src']
    if 'gen_src' in module_data:
        config['homepage'] = module_data['gen_src']
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
        dotgit = os.path.join(out_path, '.git')
        assert os.path.exists(dotgit), dotgit
        subprocess.check_call(["git", "pull"], cwd=out_path)


def parse_tags(d):
    """
    >>> r = parse_tags('''\\
    ... v0.0
    ... v0.0.0
    ... v0.0.0-rc1
    ... v1.0.1-265-g5f0c7a7
    ... v0.0-7004-g1cf70ea2
    ... ''')
    >>> for v in r:
    ...   print(v)
    (<Version('0.0.0rc1')>, 'v0.0.0-rc1')
    (<Version('0.0')>, 'v0.0')
    (<Version('0.0.0')>, 'v0.0.0')
    (<Version('0.0.post7004')>, 'v0.0-7004-g1cf70ea2')
    (<Version('1.0.1.post265')>, 'v1.0.1-265-g5f0c7a7')

    """
    tags = []
    for t in d.splitlines():
        nt = t.strip()
        if nt.startswith('v'):
            nt = t[1:]
        dashg = nt.find('-g')
        if dashg != -1:
            nt = nt[:dashg]
        try:
            v = version.parse(nt)
        except version.InvalidVersion:
            print("Invalid tag version:", t)
            continue
        if isinstance(v, version.LegacyVersion):
            continue
        tags.append((v, t))
    tags.sort()
    return list(tags)


def get_hash(ref, env={}):
    return subprocess.check_output(
        ['git', 'rev-parse', ref],
        env=env).decode('utf-8').strip()


def get_tags(env):
    d = subprocess.check_output(
        ['git', 'tag', '--list'],
        env=env).decode('utf-8')

    tags = OrderedDict()
    for v, t in parse_tags(d):
        tags[t] = (v, get_hash(t, env))
    return tags


def git_describe(ref='HEAD', env={}):
    d = subprocess.check_output(
        ['git', 'describe', '--tags', ref, '--match', 'v*', '--exclude', '*-r*'],
        env=env).decode('utf-8').strip()

    o = d
    if o.startswith('v'):
        o = o[1:]

    t, c, h = o.rsplit('-', 2)
    return (d, version.parse(t+'-'+c))


def get_src(module_data):
    src_dir = os.path.join("srcs", module_data['repo'])
    env = {'GIT_DIR': src_dir}
    if os.path.exists(src_dir):
        subprocess.check_call(
            ['git', 'fetch', '--all'],
            env=env)
    else:
        subprocess.check_call(
            ['git', 'clone', '--bare', '--mirror', module_data['src'], src_dir])
    subprocess.check_call(
        ['git', 'fetch', '--tags'],
        env=env)

    tags = get_tags(env)
    if 'v0.0' not in tags:
        # Add a default tag
        p = subprocess.Popen(
            ['git', 'log', '--reverse', '--pretty=%H %s'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        for l in p.stdout:
            l = l.decode('utf-8').strip()
            if not l:
                continue
            break
        p.stdout.close()
        first_hash, desc = l.split(" ", 1)
        cmd = [
            'git', 'tag', '-a',
            '-m','Dummy version on first commit so git-describe works',
            'v0.0', first_hash,
        ]
        subprocess.check_call(
            cmd,
            env=env)
        tags = get_tags(env)

    git_hash = get_hash(module_data['branch'], env)
    git_msg = subprocess.check_output(
        ['git', 'log', '-1', git_hash], env=env).decode('utf-8')

    desc, vdesc = git_describe(module_data['branch'], env)
    module_data['src_local'] = os.path.abspath(src_dir)
    module_data['git_describe'] = desc
    module_data['git_hash'] = git_hash
    module_data['version_tuple'] = repr(tuple(vdesc.release))
    module_data['version'] = str(vdesc)
    module_data['git_msg'] = git_msg


def render(module_data, in_file, out_file):
    template = jinja2.Template(open(in_file).read())
    s = template.render(**module_data)
    if s and not s.endswith('\n'):
        s += '\n'
    with open(out_file, 'w') as of:
        of.write(s)


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
    dotgit = os.path.join(repo_dir, '.git')
    assert os.path.exists(dotgit), dotgit
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
            git_add_file(module_data, repo_f)
    print('-'*75)

    # Commit the changes
    tocommit = subprocess.check_output(
        ['git', 'status', '--porcelain'], cwd=repo_dir).decode('utf-8')
    if tocommit:
        with tempfile.NamedTemporaryFile() as f:

            git_msg_out = []
            if 'git_msg' in module_data:
                for l in module_data['git_msg'].split('\n'):
                    if l:
                        git_msg_out.append('> '+l)
                    else:
                        git_msg_out.append('>')
                git_msg_out = "\n".join(git_msg_out)
                module_data['git_rmsg'] = git_msg_out

                f.write("""\
Updating data to {git_describe}

Updated to {version} based on {git_hash} from {src}.
{git_rmsg}
""".format(**module_data).encode('utf-8'))

            f.write("""\
Updated using {tool_version} from https://github.com/litex-hub/litex-data-auto
""".format(**module_data).encode('utf-8'))
            f.flush()
            f.name
            subprocess.check_call(['git', 'commit', '-F', f.name], cwd=repo_dir)

    # Run the git subtree command
    if 'src' in module_data:
        if os.path.exists(os.path.join(repo_dir, module_data['dir'])):
            subtree_cmd = 'pull'
        else:
            subtree_cmd = 'add'
        cmd = [
            'git', 'subtree', subtree_cmd,
            '-P', module_data['dir'],
            module_data['src_local'], module_data['git_hash'],
        ]
        print(cmd)
        subprocess.check_call(cmd, cwd=repo_dir)


def push(module_data):
    print()
    print("Pushing:", module_data['repo'])
    print('-'*75)
    repo_dir = os.path.abspath(os.path.join('repos', module_data['repo']))
    cmd = ['git', 'push', '--all']

    user = os.environ.get('GH_USER', None)
    token = os.environ.get('GH_TOKEN', None)
    if user and token:
        cmd.append('https://{u}:{p}@github.com/litex-hub/{m}.git'.format(
            u=user, p=token, m=module_data['repo']))
    subprocess.check_call(cmd, cwd=repo_dir)
    print('-'*75)


def main(name, argv):
    token = os.environ.get('GH_TOKEN', None)
    if token:
        g = github.Github(token)
    else:
        g = github.Github()

    tool_version, _ = git_describe()

    config = configparser.ConfigParser()
    config.read('modules.ini')
    for module in config.sections():
        m = config[module]

        repo_name = 'litex-data-{t}-{mod}'.format(
            t=m['type'],
            mod=module)
        m['tool_version'] = tool_version
        m['name'] = module
        m['repo'] = repo_name
        m['repo_url'] = "{mode}://github.com/litex-hub/{repo}.git".format(
            mode=GIT_MODE,
            repo=repo_name)
        m['repo_https'] = "https://github.com/litex-hub/{repo}.git".format(
            repo=repo_name)
        m['py'] = 'litex.data.{type}.{name}'.format(type=m['type'], name=module)
        m['dir'] = os.path.join('litex', 'data', m['type'], module, m['contents'])
        if 'src' in m:
            get_src(m)
        else:
            assert 'git_describe' in m, m
            assert 'git_hash' in m, m
            versions = parse_tags(m['git_describe'])
            assert len(versions) == 1, "Got multiple versions from " + m['git_describe']
            vdesc, t = versions[0]
            m['version_tuple'] = repr(tuple(vdesc.release))
            m['version'] = str(vdesc)
        print()
        print(module)
        pprint.pprint(list(m.items()))
        github_repo(g, m)
        download(m)
        update(m)

    if '--push' in argv:
        for module in config.sections():
            m = config[module]
            github_repo(g, m)
            push(m)

    return 0


if __name__ == "__main__":
    import doctest
    failure_count, test_count = doctest.testmod()
    if failure_count > 0:
        sys.exit(-1)
    sys.exit(main(sys.argv[0], sys.argv[1:]))
