#!/usr/bin/python
# -*- coding: utf-8 -*-
# author:   Jan Hybs

import sys, os, platform, re, urllib2, urllib, tarfile, shutil
from subprocess import Popen, PIPE, STDOUT


class Command(object):
    LS = 'ls'
    LS_CWD = 'ls {cwd}'
    ECHO_SYSTEM = 'echo {system}'


def get_system_simple():
    return re.match(r'([a-zA-Z]+)', platform.system().strip().lower()).group(1)


def get_x64():
    return '64' if sys.maxsize > 2 ** 32 else '32'


def mkdirr(location):
    location = os.path.abspath(location)
    folders = re.split(r'[/\\]+', location)
    for i in range(2, len(folders) + 1):
        folder = os.path.sep.join(folders[0:i])
        if os.path.exists(folder):
            continue

        os.mkdir(folder, 0777)


def padding(s='', pad='\n        '):
    if s is None or not s.strip():
        return ''
    return pad + pad.join(s.strip().splitlines())


default_kwargs = dict(
    cwd=os.getcwd(),
    x64=get_x64(),
    system=platform.system(),
    system_simply=get_system_simple(),
    system_sigs={
        'linux': { '32': None, '64': 'linux_x86_64' },
        'windows': { '32': 'windows_x86_32', '64': 'windows_x86_64' },
        'cygwin': { '32': None, '64': None }
    }
)


def fix_args(plat=None, x64=None, ext=None):
    plat = plat or get_system_simple()
    x64 = x64 or get_x64()
    ext = ext or { 'linux': '.tar.gz', 'windows': '.exe' }.get(plat)
    folder = default_kwargs['system_sigs'].get(plat).get(x64)
    location = os.path.join(folder, folder + ext)
    mkdirr(os.path.dirname(location))

    return plat, x64, ext, folder, location


def run_command(cmd, **kwargs):
    full_kwargs = default_kwargs.copy()
    full_kwargs.update(kwargs)

    if type(cmd) is list:
        full_cmd = cmd
        shell = True
    else:
        full_cmd = [cmd.format(**full_kwargs)]
        shell = False
    print "Running: {full_cmd}".format(full_cmd=str(full_cmd))

    process = Popen(full_cmd, stdout=PIPE, stderr=PIPE, shell=shell)
    stdout, stderr = process.communicate()

    return process, stdout, stderr


def check_error(process, stdout, stderr):
    if process.returncode != 0:
        print 'Error while execution!'
        if stderr.split():
            print 'Stderr: \n{stderr}'.format(stderr=padding(stderr))
            if stdout.split():
                print 'Stdout: \n{stdout}'.format(stdout=padding(stdout))
            return process.returncode

        print 'Execution successful!'
        if stderr.split():
            print 'Stderr: \n{stderr}'.format(stderr=padding(stderr))
        if stdout.split():
            print 'Stdout: \n{stdout}'.format(stdout=padding(stdout))
        return 0


def action_download_package(server='http://flow.nti.tul.cz/packages', version='0.0.master',
                            plat=None, x64=None, ext=None):
    plat, x64, ext, folder, location = fix_args(plat, x64, ext)

    fmt_object = dict(
        server=server,
        version=version,
        filename=folder + ext,
        ext=ext,
        x64=x64,
        plat=plat
    )

    download_url = "{server}/{version}/flow123d_{version}_{filename}".format(**fmt_object)

    print 'Downloading file {file} ...'.format(file=download_url)
    filename, headers = urllib.urlretrieve(download_url, location)
    print 'Downloaded', filename, padding(str(headers))
    return 0


def action_install(plat=None, x64=None, ext=None):
    plat, x64, ext, folder, location = fix_args(plat, x64, ext)

    if plat == 'linux':
        print 'Extracting: {file}'.format(file=location)
        tar_file = tarfile.open(location, 'r:gz')
        tar_file.extractall(folder)
        print 'Extracting done'
        return 0

    if plat == 'windows':
        installer_location = os.path.abspath(location)
        command = [
            installer_location,
            '/S', '/NCRC', '/D=',
            os.path.abspath(folder)
        ]
        print 'Installing...'
        process, stdout, stderr = run_command(command)
        check_error(process, stdout, stderr)
        if process.returncode != 0:
            return process.returncode
        print 'Installing done'


def action_run_flow(plat=None, x64=None, ext=None):
    plat, x64, ext, folder, location = fix_args(plat, x64, ext)

    if plat == 'linux':
        files = os.listdir(folder)
        for f in files:

            if f.lower().find('flow123d') >= 0 and os.path.isdir(os.path.join(folder, f)):
                flow_loc = os.path.join(folder, f, 'bin', 'flow123d')
                process, stdout, stderr = run_command(flow_loc + ' --version')

                if process.returncode != 0:
                    return check_error(process, stdout, stderr)

                check_error(process, stdout, stderr)

                out = stderr + stdout
                if out.find('This is Flow123d') >= 0:
                    print 'String "{s}" found'.format(s='This is Flow123d')
                    return 0
                print process.returncode


def action_uninstall(plat=None, x64=None, ext=None):
    plat, x64, ext, folder, location = fix_args(plat, x64, ext)

    print 'Uninstalling flow123d...'

    if plat == 'linux':
        # only remove install folder
        pass

    if plat == 'windows':
        uninstaller_location = os.path.abspath(os.path.join(folder, 'Uninstall.exe'))
        command = [uninstaller_location, '/S']
        process, stdout, stderr = run_command(command)
        check_error(process, stdout, stderr)
        if process.returncode != 0:
            return process.returncode

    shutil.rmtree(os.path.abspath(folder), True)
    if os.path.exists(folder):
        print 'Uninstallation not successful!'
        return 1

    print 'Uninstallation successful!'
    return 0

plat = None

print action_download_package(plat=plat)
print action_install(plat=plat)
print action_run_flow(plat=plat)
print action_uninstall(plat=plat)
