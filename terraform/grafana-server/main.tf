terraform {
  required_version = "1.3.6"
}

provider "aws" {
  region = "eu-west-1"
}

resource "aws_instance" "grafana" {
  ami           = "ami-06935448000742e6b"
  instance_type = "t2.micro"

  subnet_id = "subnet-429b1424"

  iam_instance_profile = "EC2_SSM_Role"

  associate_public_ip_address = true

  user_data = base64encode(templatefile("${path.cwd}/userdata.tmpl", {}))

  root_block_device {
    volume_size           = 8
    volume_type           = "gp3"
    iops                  = 3000
    delete_on_termination = true
  }

  vpc_security_group_ids = [module.grafana_sg.security_group_id]

  tags = {
    Name = "grafana"
  }
}

module "grafana_sg" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "4.16.2"

  vpc_id = "vpc-bc0554da"

  use_name_prefix     = false
  name                = "grafana-sg"
  description         = "Grafana Security Group"
  egress_rules        = ["all-all"]
  ingress_cidr_blocks = ["0.0.0.0/0"]
  ingress_rules       = ["ssh-tcp"]
  ingress_with_cidr_blocks = [
    {
      from_port   = 3000
      to_port     = 3000
      protocol    = "tcp"
      description = "Grafana"
      cidr_blocks = "0.0.0.0/0"
    },
    {
      from_port   = 3100
      to_port     = 3100
      protocol    = "tcp"
      description = "Loki"
      cidr_blocks = "0.0.0.0/0"
    },
    {
      from_port   = 9090
      to_port     = 9090
      protocol    = "tcp"
      description = "Prometheus"
      cidr_blocks = "0.0.0.0/0"
    },
    {
      from_port   = 9009
      to_port     = 9009
      protocol    = "tcp"
      description = "Mimir"
      cidr_blocks = "0.0.0.0/0"
    }
  ]

  tags = {
    Name = "Grafana"
  }
}
