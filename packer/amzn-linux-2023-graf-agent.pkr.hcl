packer {
  required_plugins {
    amazon = {
      version = ">= 1.2.6"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

source "amazon-ebs" "al2023" {
  ami_name      = "grafana-agent-al2023-{{timestamp}}"
  instance_type = "t2.micro"
  region        = "eu-west-1"
  source_ami_filter {
    filters = {
      name                = "al2023-ami-2023.0.*-kernel-6.1-x86_64"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    most_recent = true
    owners      = ["137112412989"]
  }
  ssh_username = "ec2-user"

  launch_block_device_mappings {
    device_name           = "/dev/xvda"
    volume_type           = "gp3"
    volume_size           = 10
    delete_on_termination = true
  }
}

build {
  name = "graf-agent-al2023"
  sources = [
    "source.amazon-ebs.al2023"
  ]

  provisioner "file" {
    source      = "files/grafana-agent.yaml"
    destination = "/tmp/grafana-agent.yaml"
  }

  provisioner "file" {
    source      = "files/grafana.repo"
    destination = "/tmp/grafana.repo"
  }

  provisioner "shell" {
    inline = [
      "sudo wget -q -O /tmp/gpg.key https://rpm.grafana.com/gpg.key",
      "sudo rpm --import /tmp/gpg.key",
      "sudo mv /tmp/grafana.repo /etc/yum.repos.d/grafana.repo",
      "sudo dnf install grafana-agent -y",
      "sudo rm -rf /etc/grafana-agent.yaml",
      "sudo mv /tmp/grafana-agent.yaml /etc/grafana-agent.yaml",
    ]
  }
}

