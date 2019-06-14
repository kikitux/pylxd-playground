# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "alvaro/bionic64"

  config.vm.provider "virtualbox" do |v|
    v.memory = 1500
    v.cpus = 2
    v.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
  end

  config.vm.network "forwarded_port", guest: 3000, host: 3000 #grafana
  config.vm.network "forwarded_port", guest: 4646, host: 4646 #nomad
  config.vm.network "forwarded_port", guest: 8200, host: 8200 #vault
  config.vm.network "forwarded_port", guest: 8500, host: 8500 #consul
  config.vm.network "forwarded_port", guest: 9090, host: 9090 #prometheus

  config.vm.provision "shell", path: "scripts/provision.sh"
  config.vm.provision "shell", path: "play.py3"
      
end
