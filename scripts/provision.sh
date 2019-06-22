#!/usr/bin/env bash

# install and configure lxd
which lxd &>/dev/null || {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -t bionic-backports -y lxd

  # check if /var/lib is btrfs
  btrfs su li /var/lib/ &>/dev/null
  if [ $? -eq 0 ]; then 
    lxd init --auto --storage-backend btrfs --storage-pool default --storage-create-device /var/lib/lxd/storage-pools/default
  else
    lxd init --auto
  fi

  lxc network set lxdbr0 ipv6.address none
}

apt-get update
apt-get install -t bionic-backports -y python-pylxd python3-pylxd
