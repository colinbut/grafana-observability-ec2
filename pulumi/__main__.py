"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws

size = 't2.micro'
subnet_id = "subnet-429b1424"



ami = aws.ec2.get_ami(filters=[
                          aws.ec2.GetAmiFilterArgs(
                              name="name",
                              values=["amzn-*"]
                          ),
                          aws.ec2.GetAmiFilterArgs(
                              name="root-device-type",
                              values=["ebs"]
                          ),
                          aws.ec2.GetAmiFilterArgs(
                              name="virtualization-type",
                              values=["hvm"]
                          )
                      ],
                      most_recent=True,
                      owners=["amazon"])

grafana_sg = aws.ec2.SecurityGroup('grafana',
                                   description='Grafana Security Group',
                                   ingress=[
                                       # ssh
                                       {'protocol': 'tcp', 'from_port': 22, 'to_port': 22, 'cidr_blocks': ['0.0.0.0/0'], 'description': 'ssh'},
                                       # grafana
                                       {'protocol': 'tcp', 'from_port': 3000, 'to_port': 3000, 'cidr_blocks': ['0.0.0.0/0'], 'description': 'Grafana'},
                                       # loki
                                       {'protocol': 'tcp', 'from_port': 3100, 'to_port': 3100, 'cidr_blocks': ['0.0.0.0/0'], 'description': 'Loki'},
                                       # prometheus
                                       {'protocol': 'tcp', 'from_port': 9090, 'to_port': 9090, 'cidr_blocks': ['0.0.0.0/0'], 'description': 'Prometheus'},
                                       # mimir
                                       {'protocol': 'tcp', 'from_port': 9009, 'to_port': 9009, 'cidr_blocks': ['0.0.0.0/0'], 'description': 'Mimir'}
                                   ],
                                   egress=[
                                       {'protocol': '-1', 'from_port': 0, 'to_port': 0, 'cidr_blocks': ['0.0.0.0/0'], 'ipv6_cidr_blocks': ['::/0']}
                                   ],
                                   tags={
                                       'Name': 'grafana-sg'
                                    })

user_data = """
#!/bin/bash

# grafana
wget -q -O gpg.key https://rpm.grafana.com/gpg.key
rpm --import gpg.key

cat > /etc/yum.repos.d/grafana.repo << EOF
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF

dnf install grafana -y

systemctl daemon-reload
systemctl start grafana-server
systemctl status grafana-server

systemctl enable grafana-server.service


# loki
mkdir -p /opt/loki && cd /opt/loki/
curl -fLo loki.zip "https://github.com/grafana/loki/releases/download/v2.8.3/loki-linux-amd64.zip"
unzip "loki.zip"
mv loki-linux-amd64 loki && rm -rf loki.zip

wget https://raw.githubusercontent.com/grafana/loki/v2.8.3/cmd/loki/loki-local-config.yaml -O loki-config.yaml

useradd --system loki
chown loki:loki -R /opt/loki

cat > /etc/systemd/system/loki.service << EOF
[Unit]
Description=Loki service
After=network.target

[Service]
Type=simple
User=loki
ExecStart=/opt/loki/loki -config.file /opt/loki/loki-config.yaml

[Install]
WantedBy=multi-user.target
EOF

systemctl start loki
systemctl enable loki.service


# Prometheus
mkdir -p /opt/prometheus && cd /opt/prometheus
curl -O -L "https://github.com/prometheus/prometheus/releases/download/v2.46.0-rc.0/prometheus-2.46.0-rc.0.linux-amd64.tar.gz"
tar xvfz prometheus-*.tar.gz
mv prom*/* .
rmdir prom*

useradd -M -U prometheus
chown prometheus:prometheus -R /opt/prometheus

cat > /etc/systemd/system/prometheus.service << EOF
[Unit]
Description=Prometheus Server
Documentation=https://prometheus.io/docs/introduction/overview/
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Restart=on-failure
ExecStart=/opt/prometheus/prometheus \
  --config.file=/opt/prometheus/prometheus.yml \
  --storage.tsdb.path=/opt/prometheus/data \
  --storage.tsdb.retention.time=30d

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start prometheus.service
systemctl enable prometheus.service


# mimir
mkdir -p /opt/mimir && cd /opt/mimir/
curl -fLo mimir https://github.com/grafana/mimir/releases/latest/download/mimir-linux-amd64
chmod +x mimir

useradd --system mimir
chown mimir:mimir -R /opt/mimir

cat > mimir-config.yaml << EOF
# Do not use this configuration in production.
# It is for demonstration purposes only.
multitenancy_enabled: false

blocks_storage:
  backend: filesystem
  bucket_store:
    sync_dir: /tmp/mimir/tsdb-sync
  filesystem:
    dir: /tmp/mimir/data/tsdb
  tsdb:
    dir: /tmp/mimir/tsdb

compactor:
  data_dir: /tmp/mimir/compactor
  sharding_ring:
    kvstore:
      store: memberlist

distributor:
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: memberlist

ingester:
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: memberlist
    replication_factor: 1

ruler_storage:
  backend: filesystem
  filesystem:
    dir: /tmp/mimir/rules

ruler:
  rule_path: /opt/mimir/data_ruler/

server:
  http_listen_port: 9009
  log_level: error

store_gateway:
  sharding_ring:
    replication_factor: 1

activity_tracker:
  filepath: /opt/mimir/metrics-activity.log
EOF

cat > /etc/systemd/system/mimir.service << EOF
[Unit]
Description=Mimir service
After=network.target

[Service]
Type=simple
User=mimir
ExecStart=/opt/mimir/mimir -config.file=/opt/mimir/mimir-config.yaml

[Install]
WantedBy=multi-user.target
EOF

systemctl start mimir
systemctl enable mimir.service
"""

grafana_server = aws.ec2.Instance('grafana',
                                  instance_type=size,
                                  vpc_security_group_ids=[grafana_sg.id],
                                  ami=ami.id,
                                  associate_public_ip_address=True,
                                  subnet_id=subnet_id,
                                  user_data=user_data,
                                  tags={
                                      "Name": "grafana"
                                  })

pulumi.export('publicIp', grafana_server.public_ip)
pulumi.export('publicHostName', grafana_server.public_dns)
