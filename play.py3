#!/usr/bin/env python3

from pylxd import Client
import time
import warnings

import platform

# get alias
if platform.machine() == "x86_64":
  alias="bionic/amd64"
else:
  alias="bionic/arm64"


# pylxd gives a warning on bionic for client.container.get('myc')
warnings.filterwarnings("ignore")

client = Client() # we focus on local LXD socket

def create_c(name):

    # https://github.com/lxc/lxd/blob/master/doc/rest-api.md
    config = {'name': name, 'source': {
                'type': 'image', 'mode': 'pull',
                'server': 'https://cloud-images.ubuntu.com/daily',
                'protocol': 'simplestreams',
                'alias': alias
                }
              }
    print("creating container", name)
    return client.containers.create(config, wait=True)


def copy_c(src, dst):

    # https://github.com/lxc/lxd/blob/master/doc/rest-api.md
    config = {'name': dst, 'source': {
                'type': 'copy',
                'container_only': True,
                'source': src
                }
              }

    print("creating container", dst)
    return client.containers.create(config, wait=True)


def start_c(name):
    l = client.containers.get(name)
    if any([l.status == 'Stopped', l.status == 'Frozen']):
        l.start(wait=True)
        print("status ", l.status)


def stop_c(name):
    l = client.containers.get(name)
    if any([l.status == 'Running', l.status == 'Frozen']):
        l.stop(wait=True)
        print("status ", l.status)


def execute_c(container, command, environment):
    # wait until there is an ip
    while container.state().network['eth0']['addresses'][0]["family"] != 'inet':
        print('.. waiting for container', container.name, 'to get ipv4 ..')
        time.sleep(2)
    print("command: {}".format(command))
    result = container.execute(command, environment)
    print("exit_code: {}".format(result.exit_code))
    print("stdout: {}".format(result.stdout))
    if result.stderr:
        print("stderr: {}".format(result.stderr))


server_list =["server"] # will host our servers
client_list =["client1"] # our clients

all_list = server_list + client_list

base_client_cmd = [
    'apt-get update'.split(),
    'apt-get install --no-install-recommends -y docker.io'.split(),
    'apt-get install --no-install-recommends -y default-jre'.split(),
    'apt-get clean'.split(),
]

server_cmd = [
    'curl -sLo /tmp/consul.sh https://raw.githubusercontent.com/kikitux/curl-bash/master/consul-1server/consul.sh'.split(),
    'bash /tmp/consul.sh'.split(),
    'curl -sLo /tmp/nomad.sh https://raw.githubusercontent.com/kikitux/curl-bash/master/nomad-1server/nomad.sh'.split(),
    'bash /tmp/nomad.sh'.split(),
    'curl -sLo /tmp/vault.sh https://raw.githubusercontent.com/kikitux/curl-bash/master/vault-dev/vault.sh'.split(),
    'bash /tmp/vault.sh'.split(),
    'curl -sLo /tmp/redis-server.sh https://raw.githubusercontent.com/kikitux/curl-bash/master/provision/redis-server.sh'.split(),
    'bash /tmp/redis-server.sh'.split(),
    'curl -sLo /tmp/prometheus.sh https://raw.githubusercontent.com/kikitux/curl-bash/master/provision/prometheus.sh'.split(),
    'bash /tmp/prometheus.sh'.split(),
    'curl -sLo /tmp/grafana-server.sh https://raw.githubusercontent.com/kikitux/curl-bash/master/provision/grafana-server.sh'.split(),
    'bash /tmp/grafana-server.sh'.split(),
]

client_cmd = [
    'curl -sLo /tmp/consul.sh https://raw.githubusercontent.com/kikitux/curl-bash/master/consul-client/consul.sh'.split(),
    'bash /tmp/consul.sh'.split(),
    'curl -sLo /tmp/nomad.sh https://raw.githubusercontent.com/kikitux/curl-bash/master/nomad-client/nomad.sh'.split(),
    'bash /tmp/nomad.sh'.split(),
]

# create base container
if not client.containers.exists('base'):
    create_c('base')
    stop_c('base')

# create base-client container
if not client.containers.exists('base-client'):
    copy_c('base', 'base-client')
    start_c('base-client')

    environment = {'DEBIAN_FRONTEND': 'noninteractive'}

    container = client.containers.get('base-client')
    for command in base_client_cmd:
        execute_c(container,command,environment)

    stop_c('base-client')

# create the containers
for c in all_list:

    if not client.containers.exists(c):

        if c in server_list:
            container = copy_c('base', c)

        if c in client_list:
            container = copy_c('base-client', c)

        # we port fwd to the first server
        if container.name in server_list[0]:
    
            devices = { 'grafana': {'connect': 'tcp:127.0.0.1:3000', 'listen': 'tcp:0.0.0.0:3000', 'type': 'proxy'},
                        'nomad': {'connect': 'tcp:127.0.0.1:4646', 'listen': 'tcp:0.0.0.0:4646', 'type': 'proxy'},
                        'vault': {'connect': 'tcp:127.0.0.1:8200', 'listen': 'tcp:0.0.0.0:8200', 'type': 'proxy'},
                        'consul': {'connect': 'tcp:127.0.0.1:8500', 'listen': 'tcp:0.0.0.0:8500', 'type': 'proxy'},
                        'prometheus': {'connect': 'tcp:127.0.0.1:9090', 'listen': 'tcp:0.0.0.0:9090', 'type': 'proxy'}
                      }
    
            container.devices = devices
            container.save(wait=True)

        container.start(wait=True)

        # setup client for nested docker
        if container.name in client_list:
            container.config = {'security.privileged': 'True',
                                'security.nesting': 'True'
                               }
            container.save(wait=True)


# run the commands
for c in all_list:
    start_c(c)
    container = client.containers.get(c)

    # client join first server
    if container.name in server_list[0]:
        commands = server_cmd
        environment = {'IFACE': 'eth0'}
        while container.state().network['eth0']['addresses'][0]["family"] != 'inet':
            print('.. waiting for container', container.name, 'to get ipv4 ..')
            time.sleep(2)
        srv_ip = container.state().network['eth0']['addresses'][0]["address"]

    if container.name in client_list:
        commands = client_cmd
        environment = {'IFACE': 'eth0', 'LAN_JOIN':  srv_ip}

    # we are sure network is working, so lets continue
    for command in commands:
        execute_c(container, command, environment)
