# Grafana Agent EC2 AMI

## Pre-requisites

Download and Install Packer as per instructions - https://developer.hashicorp.com/packer/downloads?product_intent=packer

## To build the AMI run:

First need to initialize Packer to install the required plugins.

In current directory:

```bash
packer init .
```

Then build:

```bash
AWS_PROFILE=<<YOUR AWS PROFILE>> packer build amzn-linux-2023-graf-agent.pkr.hcl
```

## Author

Colin But.
