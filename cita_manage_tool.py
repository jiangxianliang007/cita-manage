#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2019/2/28 11:51
# @Author  : 007
# @File    : CITA_Manage_Tool.py
# @Software: PyCharm
"""
This tool can quickly deploy CITA, support batch management of CITA nodes, and view block height, process, and restart operations.
"""

import paramiko
import threading
import os
import datetime
import shutil
import requests
import json
import time
import subprocess


def downloader(url, path):
    """
    Download the CITA program..
    """
    start = time.time()
    size = 0
    response = requests.get(url, stream=True)
    chunk_size = 1024
    content_size = int(response.headers['content-length'])
    if response.status_code == 200:
        print('[File size]: %0.2f MB' % (content_size / chunk_size / 1024))
        with open(path, "wb") as file:
            for data in response.iter_content(chunk_size=chunk_size):
                file.write(data)
                size += len(data)
                print('\r' + '[Download progress]: %s %.2f%%' %
                      ('>' * int(size * 100 / content_size),
                       float(size / content_size * 100)),
                      end='')
    end = time.time()
    print('\n' + "[All download completed!]: %.2f second" % (end - start))


def stop_cita():
    print("Begin stop CITA ......")
    cita_node = 0
    for ip in iplist:
        cmd = ([
            ('cd %s;cd cita_secp256k1_sha3/;'
             './env.sh ./bin/cita stop test-chain/%d' % (remotedir, cita_node))
        ])
        cita_node = cita_node + 1
        stop_cita_thread = threading.Thread(target=connect_cita_server,
                                            args=(ip, username, passwd, cmd))
        stop_cita_thread.start()
        stop_cita_thread.join()


def start_cita():
    print("Begin start CITA ......")
    cita_node = 0
    for ip in iplist:
        cmd = ([('cd %s;cd cita_secp256k1_sha3/;'
                 './daemon.sh ./bin/cita start test-chain/%d' %
                 (remotedir, cita_node))])
        cita_node = cita_node + 1
        start_cita_thread = threading.Thread(target=connect_cita_server,
                                             args=(ip, username, passwd, cmd))
        start_cita_thread.start()
        start_cita_thread.join()


def check_cita_process():
    print("Begin start CITA ......")
    cita_node = 0
    for ip in iplist:
        cmd = ([('ps -ef | grep cita- | grep -v grep')])
        cita_node = cita_node + 1
        process_cita_thread = threading.Thread(target=connect_cita_server,
                                               args=(ip, username, passwd,
                                                     cmd))
        process_cita_thread.start()
        process_cita_thread.join()


def init_cita(nodes, filename):
    """
    Check if CITA's docker container is already running, delete and initialize CITA configuration.
    """
    shutil.unpack_archive(filename)
    try:
        subprocess.run("docker images", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(e)
        subprocess.call(['apt -y install docker.io'], shell=True)
    docker_process = os.popen('ps -ef | grep docker | grep -v grep |wc -l')
    docker_process_ct = (docker_process.read())
    docker_process_ct = int(docker_process_ct)

    if docker_process_ct == 0:
        subprocess.call(['service docker start'], shell=True)

    docker_run_cita = os.popen('docker ps -a -q -f name=cita_run |wc -l')
    docker_run_cita_ct = (docker_run_cita.read())
    docker_run_cita_ct = int(docker_run_cita_ct)

    if docker_run_cita_ct >= 1:
        os.system('docker rm -f $(docker ps -a -q -f name=cita_run)')
    pwd = os.getcwd()
    os.chdir(file)
    os.system((
        './env.sh ./scripts/create_cita_config.py create --super_admin "0x4b5ae4567ad5d9fb92bc9afd6a657e6fa13a2523" --nodes %s'
    ) % nodes)
    os.chdir(pwd)
    os.system(('tar czf cita_secp256k1_sha3_deploy.tar.gz %s') % file)


def put_cita_file(ip, username, passwd, localpath, remotepath):
    """
    Upload the initialized CITA program to the server
    """
    print("Upload cita bin to server........................")
    try:
        t = paramiko.Transport((ip, 22))
        t.connect(username=username, password=passwd)
        sftp = paramiko.SFTPClient.from_transport(t)
        sftp.put(localpath, remotepath)
        print("Uploading CITA file to node %s" % ip)
        t.close()
    except Exception as e:
        print("Server %s %s ,please check if the user password is correct." %
              (ip, e))


def connect_cita_server(ip, username, passwd, cmd):
    """
    Connect to the server to execute the specified command
    """
    print("Upload command to server........................")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, 22, username, passwd, timeout=5)
        for m in cmd:
            print(m)
            stdin, stdout, stderr = ssh.exec_command(m)
            out = stdout.readlines()
            for o in out:
                print(o),
        print('%s\t connection succeeded .\n' % (ip))
        ssh.close()
    except:
        print(
            'Server %s connection failed, please check if the user password is correct.\n'
            % (ip))


def deploy(iplist, file):
    """
    Initialize the node information, check whether the CITA program exists,
     initialize CITA if it exists,
     go to github to search for the latest version of CITA and download it to the local
    """
    nodes = iplist[0] + ':4000'
    for ip in iplist[1:]:
        node = (',' + '%s' + ':4000') % ip
        nodes = nodes + node

    if os.path.exists(filename):
        print('{} exists'.format(filename))
        if os.path.isdir(file):
            print(('remove %s') % file)
            shutil.rmtree(file)
        init_cita(nodes, filename)
        execut()
    else:
        print('{} does not exist'.format(filename))
        if os.path.isdir(file):
            print(('remove %s') % file)
            shutil.rmtree(file)
        dir = os.getcwd()
        cita_name = "cita_secp256k1_sha3.tar.gz"
        response = requests.get(
            "https://api.github.com/repos/cryptape/cita/releases/latest",
            stream=True)
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                cita_json_dict = json.loads(decoded_line)
        cita_down_data = cita_json_dict['assets']

        for urldata in cita_down_data:
            url_list = urldata["browser_download_url"]
            if cita_name in url_list:
                url = url_list
                path = dir + '/' + cita_name
                print(path)
                print((
                    'Download the latest version of CITA from github...! URL: %s'
                ) % url)
                downloader(url, path)
        init_cita(nodes, filename)
        execut()


def execut():
    """
    Log in to the remote server to start CITA nodes.
    """
    threads = []
    print("Begin Deploy CITA ......")
    cita_node = 0
    for ip in iplist:
        put_thread = threading.Thread(target=put_cita_file,
                                      args=(ip, username, passwd, localpath,
                                            remotepath))
        put_thread.start()
        put_thread.join()

    for ip in iplist:
        cmd = ([(
            'cd %s;docker rm -f $(docker ps -a -q -f name=cita_run);'
            'mv cita_secp256k1_sha3 cita_secp256k1_sha3_%s ;'
            'tar zxf cita_secp256k1_sha3_deploy.tar.gz;cd cita_secp256k1_sha3/;'
            './env.sh ./bin/cita setup test-chain/%d;'
            './daemon.sh ./bin/cita start test-chain/%d' %
            (remotedir, baktime, cita_node, cita_node))])
        cita_node = cita_node + 1
        connect_thread = threading.Thread(target=connect_cita_server,
                                          args=(ip, username, passwd, cmd))
        threads.append(connect_thread)

    for t in threads:
        t.setDaemon(True)
        t.start()

    for t in threads:
        t.join()

    time.sleep(10)
    check_blockNumber()


def check_blockNumber():
    """
    View the height of the running block
    """
    port = 1337
    headers = {'Content-Type': 'application/json'}
    data = {"jsonrpc": "2.0", "method": "blockNumber", "params": [], "id": 83}
    for node in iplist:
        try:
            response = requests.post(url='http://%s:%d' % (node, port),
                                     headers=headers,
                                     data=json.dumps(data),
                                     timeout=5)
        except Exception as e:
            #print(e)
            print(
                "The node %s jsonrpc interface connection timed out. Please check if the chain is running and whether the firewall is open."
                % (node))
        else:
            blockNumber = response.text
            blockNumber = json.loads(blockNumber)
            try:
                blockNumber = blockNumber['result']
            except Exception as e:
                print(blockNumber)
            else:
                blockNumber = int(blockNumber, 16)
                print("%s current blocknumber is: %d \n" % (node, blockNumber))
        port = port + 1


def quit():
    os.exit()


if __name__ == '__main__':
    """
    The default variable configuration can be customized, such as: username, passwd, remotedir, iplist
    """
    username = "cita"
    passwd = "dmxdhldny"
    localpath = './cita_secp256k1_sha3_deploy.tar.gz'
    remotedir = '/home/cita/'
    remotepath = remotedir + 'cita_secp256k1_sha3_deploy.tar.gz'
    file = 'cita_secp256k1_sha3'
    filename = file + '.tar.gz'
    baktime = datetime.datetime.now().strftime("%m%d%H%M")
    iplist = ['192.168.1.1', '192.168.1.2', '192.168.1.3', '192.168.1.4']
    exit_flag = False
    menu = {
        1: 'deploy_cita',
        2: 'check_blockNumber',
        3: 'stop_cita',
        4: 'start_cita',
        5: 'check_cita_process',
        6: 'quit'
    }

    while not exit_flag:
        print("\n")
        for index, item in menu.items():
            print(index, item)
        choice = input("Choose to enter>>:")
        if choice.isdigit():
            choice = int(choice)
            if choice in list(menu.keys()):
                if choice == 1:
                    deploy(iplist, file)
                elif choice == 2:
                    check_blockNumber()
                elif choice == 3:
                    stop_cita()
                elif choice == 4:
                    start_cita()
                elif choice == 5:
                    check_cita_process()
                elif choice == 6:
                    exit_flag = True
            else:
                print(
                    "The entered code %d does not exist, please re-select !" %
                    choice)
        else:
            print(
                "=======Invalid option, please enter the number in the menu bar list======"
            )
