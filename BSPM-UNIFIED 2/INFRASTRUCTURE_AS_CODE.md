# Infrastructure as Code - GBStudio Automation Hub

**Version:** 3.2
**Last Updated:** 2025-01-09

This document provides Infrastructure as Code (IaC) templates for deploying the GBStudio Automation Hub using various tools and platforms.

---

## Table of Contents

1. [Terraform (AWS)](#1-terraform-aws)
2. [Kubernetes Manifests](#2-kubernetes-manifests)
3. [Helm Charts](#3-helm-charts)
4. [AWS CloudFormation](#4-aws-cloudformation)
5. [Docker Swarm](#5-docker-swarm)
6. [Ansible Playbooks](#6-ansible-playbooks)

---

## 1. Terraform (AWS)

### 1.1 Directory Structure

```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── vpc.tf
├── security_groups.tf
├── ec2.tf
├── rds.tf
├── elasticache.tf
├── s3.tf
├── iam.tf
├── route53.tf
├── cloudwatch.tf
└── modules/
    ├── networking/
    ├── compute/
    └── monitoring/
```

### 1.2 main.tf

```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "gbstudio-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "gbstudio-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "GBStudio"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
```

### 1.3 variables.tf

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "gbstudio"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "c5.4xlarge"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage (GB)"
  type        = number
  default     = 100
}

variable "elasticache_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.medium"
}

variable "domain_name" {
  description = "Domain name"
  type        = string
  default     = "gbstudio.yourdomain.com"
}

variable "admin_ip_whitelist" {
  description = "IP addresses allowed to access SSH"
  type        = list(string)
  default     = ["203.0.113.0/24"]
}

variable "db_master_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}
```

### 1.4 vpc.tf

```hcl
# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-${var.environment}-igw"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count             = length(var.public_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-${var.environment}-public-subnet-${count.index + 1}"
    Tier = "Public"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-${var.environment}-private-subnet-${count.index + 1}"
    Tier = "Private"
  }
}

# NAT Gateway EIP
resource "aws_eip" "nat" {
  count  = length(var.public_subnet_cidrs)
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-${var.environment}-nat-eip-${count.index + 1}"
  }
}

# NAT Gateway
resource "aws_nat_gateway" "main" {
  count         = length(var.public_subnet_cidrs)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${var.project_name}-${var.environment}-nat-${count.index + 1}"
  }
}

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-public-rt"
  }
}

# Public Route Table Association
resource "aws_route_table_association" "public" {
  count          = length(var.public_subnet_cidrs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private Route Tables
resource "aws_route_table" "private" {
  count  = length(var.private_subnet_cidrs)
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-private-rt-${count.index + 1}"
  }
}

# Private Route Table Association
resource "aws_route_table_association" "private" {
  count          = length(var.private_subnet_cidrs)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
```

### 1.5 security_groups.tf

```hcl
# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from internet"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP from internet (redirect to HTTPS)"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-alb-sg"
  }
}

# EC2 Security Group
resource "aws_security_group" "ec2" {
  name        = "${var.project_name}-${var.environment}-ec2-sg"
  description = "Security group for EC2 instances"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "Backend API from ALB"
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_ip_whitelist
    description = "SSH from admin IPs"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-ec2-sg"
  }
}

# RDS Security Group
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
    description     = "PostgreSQL from EC2"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }
}

# ElastiCache Security Group
resource "aws_security_group" "elasticache" {
  name        = "${var.project_name}-${var.environment}-elasticache-sg"
  description = "Security group for ElastiCache Redis"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
    description     = "Redis from EC2"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-elasticache-sg"
  }
}
```

### 1.6 ec2.tf

```hcl
# EC2 Instance
resource "aws_instance" "gbstudio" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type

  subnet_id                   = aws_subnet.private[0].id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  iam_instance_profile        = aws_iam_instance_profile.gbstudio.name
  associate_public_ip_address = false

  root_block_device {
    volume_type = "gp3"
    volume_size = 100
    encrypted   = true
  }

  ebs_block_device {
    device_name = "/dev/sdf"
    volume_type = "gp3"
    volume_size = 500
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh", {
    db_host     = aws_db_instance.gbstudio.endpoint
    redis_host  = aws_elasticache_cluster.gbstudio.cache_nodes[0].address
    environment = var.environment
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-instance"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Application Load Balancer
resource "aws_lb" "gbstudio" {
  name               = "${var.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = true

  tags = {
    Name = "${var.project_name}-${var.environment}-alb"
  }
}

# Target Group
resource "aws_lb_target_group" "gbstudio" {
  name     = "${var.project_name}-${var.environment}-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-tg"
  }
}

# Target Group Attachment
resource "aws_lb_target_group_attachment" "gbstudio" {
  target_group_arn = aws_lb_target_group.gbstudio.arn
  target_id        = aws_instance.gbstudio.id
  port             = 8000
}

# ALB Listener (HTTPS)
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.gbstudio.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = aws_acm_certificate.gbstudio.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.gbstudio.arn
  }
}

# ALB Listener (HTTP -> HTTPS redirect)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.gbstudio.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
```

### 1.7 rds.tf

```hcl
# DB Subnet Group
resource "aws_db_subnet_group" "gbstudio" {
  name       = "${var.project_name}-${var.environment}-db-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-${var.environment}-db-subnet"
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "gbstudio" {
  identifier     = "${var.project_name}-${var.environment}-db"
  engine         = "postgres"
  engine_version = "15.4"

  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "gbstudio_production"
  username = "gbstudio_admin"
  password = var.db_master_password

  db_subnet_group_name   = aws_db_subnet_group.gbstudio.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 30
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = 60
  monitoring_role_arn             = aws_iam_role.rds_monitoring.arn

  auto_minor_version_upgrade = true
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYYMMDDhhmmss", timestamp())}"

  tags = {
    Name = "${var.project_name}-${var.environment}-db"
  }
}

# Read Replica (Optional)
resource "aws_db_instance" "gbstudio_replica" {
  count = var.enable_read_replica ? 1 : 0

  identifier     = "${var.project_name}-${var.environment}-db-replica"
  replicate_source_db = aws_db_instance.gbstudio.id

  instance_class = var.db_instance_class
  storage_encrypted = true

  backup_retention_period = 7
  skip_final_snapshot     = true

  tags = {
    Name = "${var.project_name}-${var.environment}-db-replica"
  }
}
```

### 1.8 elasticache.tf

```hcl
# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "gbstudio" {
  name       = "${var.project_name}-${var.environment}-redis-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-subnet"
  }
}

# ElastiCache Redis Cluster
resource "aws_elasticache_cluster" "gbstudio" {
  cluster_id           = "${var.project_name}-${var.environment}-redis"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.elasticache_node_type
  num_cache_nodes      = 1
  parameter_group_name = aws_elasticache_parameter_group.gbstudio.name
  subnet_group_name    = aws_elasticache_subnet_group.gbstudio.name
  security_group_ids   = [aws_security_group.elasticache.id]

  port = 6379

  snapshot_retention_limit = 5
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:07:00"

  tags = {
    Name = "${var.project_name}-${var.environment}-redis"
  }
}

# ElastiCache Parameter Group
resource "aws_elasticache_parameter_group" "gbstudio" {
  name   = "${var.project_name}-${var.environment}-redis-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-params"
  }
}
```

### 1.9 s3.tf

```hcl
# S3 Bucket for Backups
resource "aws_s3_bucket" "backups" {
  bucket = "${var.project_name}-${var.environment}-backups"

  tags = {
    Name = "${var.project_name}-${var.environment}-backups"
  }
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket Lifecycle
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "delete-old-backups"
    status = "Enabled"

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "GLACIER"
    }
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

### 1.10 outputs.tf

```hcl
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.gbstudio.dns_name
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.gbstudio.id
}

output "db_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.gbstudio.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.gbstudio.cache_nodes[0].address
  sensitive   = true
}

output "backup_bucket" {
  description = "S3 backup bucket name"
  value       = aws_s3_bucket.backups.id
}
```

---

## 2. Kubernetes Manifests

### 2.1 Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: gbstudio-production
  labels:
    name: gbstudio-production
    environment: production
```

### 2.2 ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gbstudio-config
  namespace: gbstudio-production
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  DATABASE_POOL_SIZE: "50"
  DATABASE_MAX_OVERFLOW: "20"
  CACHE_TTL_SECONDS: "600"
  SESSION_TTL_SECONDS: "86400"
  MAX_CONCURRENT_GENERATIONS: "3"
  RATE_LIMIT_REQUESTS_PER_MINUTE: "30"
  METRICS_ENABLED: "true"
```

### 2.3 Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: gbstudio-secrets
  namespace: gbstudio-production
type: Opaque
stringData:
  POSTGRES_PASSWORD: "CHANGE_ME"
  REDIS_PASSWORD: "CHANGE_ME"
  API_KEY_SECRET: "CHANGE_ME"
  JWT_SECRET_KEY: "CHANGE_ME"
  BACKUP_ENCRYPTION_KEY: "CHANGE_ME"
```

### 2.4 PostgreSQL StatefulSet

```yaml
# postgres-statefulset.yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: gbstudio-production
spec:
  ports:
  - port: 5432
  clusterIP: None
  selector:
    app: postgres
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: gbstudio-production
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_USER
          value: gbstudio_prod
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: gbstudio-secrets
              key: POSTGRES_PASSWORD
        - name: POSTGRES_DB
          value: gbstudio_production
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - gbstudio_prod
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - gbstudio_prod
          initialDelaySeconds: 5
          periodSeconds: 10
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "fast-ssd"
      resources:
        requests:
          storage: 100Gi
```

### 2.5 Redis Deployment

```yaml
# redis-deployment.yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: gbstudio-production
spec:
  ports:
  - port: 6379
  selector:
    app: redis
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: gbstudio-production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command:
        - redis-server
        - --requirepass
        - $(REDIS_PASSWORD)
        - --maxmemory
        - 2gb
        - --maxmemory-policy
        - allkeys-lru
        ports:
        - containerPort: 6379
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: gbstudio-secrets
              key: REDIS_PASSWORD
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 10
```

### 2.6 Backend Deployment

```yaml
# backend-deployment.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: gbstudio-production
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: backend
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: gbstudio-production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: ghcr.io/your-org/gbstudio/backend:v3.2.0
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: gbstudio-config
              key: ENVIRONMENT
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: gbstudio-config
              key: LOG_LEVEL
        - name: DATABASE_URL
          value: "postgresql+asyncpg://gbstudio_prod:$(POSTGRES_PASSWORD)@postgres:5432/gbstudio_production"
        - name: REDIS_URL
          value: "redis://:$(REDIS_PASSWORD)@redis:6379/0"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: gbstudio-secrets
              key: POSTGRES_PASSWORD
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: gbstudio-secrets
              key: REDIS_PASSWORD
        - name: API_KEY_SECRET
          valueFrom:
            secretKeyRef:
              name: gbstudio-secrets
              key: API_KEY_SECRET
        resources:
          requests:
            memory: "2Gi"
            cpu: "2000m"
          limits:
            memory: "4Gi"
            cpu: "4000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        volumeMounts:
        - name: project-files
          mountPath: /app/project_files
        - name: vectorstore
          mountPath: /app/vectorstore
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: project-files
        persistentVolumeClaim:
          claimName: project-files-pvc
      - name: vectorstore
        persistentVolumeClaim:
          claimName: vectorstore-pvc
      - name: logs
        persistentVolumeClaim:
          claimName: logs-pvc
```

### 2.7 Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gbstudio-ingress
  namespace: gbstudio-production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "30"
spec:
  tls:
  - hosts:
    - gbstudio.yourdomain.com
    secretName: gbstudio-tls
  rules:
  - host: gbstudio.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
```

### 2.8 HorizontalPodAutoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: gbstudio-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
```

---

## 3. Helm Charts

### 3.1 Chart Structure

```
gbstudio-helm/
├── Chart.yaml
├── values.yaml
├── values-production.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── postgres-statefulset.yaml
│   ├── redis-deployment.yaml
│   ├── backend-deployment.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── service.yaml
│   └── pvc.yaml
└── README.md
```

### 3.2 Chart.yaml

```yaml
apiVersion: v2
name: gbstudio
description: GBStudio Automation Hub - AI-powered sprite generation
type: application
version: 3.2.0
appVersion: "3.2.0"
keywords:
  - gbstudio
  - sprite-generation
  - ai
  - gamedev
maintainers:
  - name: Your Name
    email: your.email@example.com
sources:
  - https://github.com/your-org/gbstudio
```

### 3.3 values.yaml

```yaml
# Default values for gbstudio
replicaCount: 3

image:
  repository: ghcr.io/your-org/gbstudio/backend
  pullPolicy: IfNotPresent
  tag: "v3.2.0"

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""

environment: production

config:
  logLevel: INFO
  databasePoolSize: 50
  databaseMaxOverflow: 20
  cacheTTL: 600
  sessionTTL: 86400
  maxConcurrentGenerations: 3
  rateLimitRequestsPerMinute: 30
  metricsEnabled: true

secrets:
  postgresPassword: "CHANGE_ME"
  redisPassword: "CHANGE_ME"
  apiKeySecret: "CHANGE_ME"
  jwtSecretKey: "CHANGE_ME"

postgresql:
  enabled: true
  image: postgres:15-alpine
  resources:
    requests:
      memory: 2Gi
      cpu: 1000m
    limits:
      memory: 4Gi
      cpu: 2000m
  persistence:
    enabled: true
    size: 100Gi
    storageClass: fast-ssd

redis:
  enabled: true
  image: redis:7-alpine
  resources:
    requests:
      memory: 1Gi
      cpu: 500m
    limits:
      memory: 2Gi
      cpu: 1000m

service:
  type: ClusterIP
  port: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "30"
  hosts:
    - host: gbstudio.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: gbstudio-tls
      hosts:
        - gbstudio.yourdomain.com

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

resources:
  requests:
    memory: 2Gi
    cpu: 2000m
  limits:
    memory: 4Gi
    cpu: 4000m

persistence:
  projectFiles:
    enabled: true
    size: 50Gi
    storageClass: fast-ssd
  vectorstore:
    enabled: true
    size: 20Gi
    storageClass: fast-ssd
  logs:
    enabled: true
    size: 10Gi
    storageClass: standard

nodeSelector: {}

tolerations: []

affinity: {}
```

### 3.4 Installation Commands

```bash
# Add Helm repository (if using private repo)
helm repo add gbstudio https://charts.gbstudio.yourdomain.com
helm repo update

# Install in production namespace
helm install gbstudio gbstudio/gbstudio \
  --namespace gbstudio-production \
  --create-namespace \
  --values values-production.yaml

# Upgrade
helm upgrade gbstudio gbstudio/gbstudio \
  --namespace gbstudio-production \
  --values values-production.yaml

# Rollback
helm rollback gbstudio 1 --namespace gbstudio-production

# Uninstall
helm uninstall gbstudio --namespace gbstudio-production
```

---

## 4. AWS CloudFormation

### 4.1 Main Template

```yaml
# cloudformation/main.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'GBStudio Automation Hub - Production Infrastructure'

Parameters:
  Environment:
    Type: String
    Default: production
    AllowedValues:
      - production
      - staging
    Description: Environment name

  InstanceType:
    Type: String
    Default: c5.4xlarge
    Description: EC2 instance type

  DBInstanceClass:
    Type: String
    Default: db.t3.medium
    Description: RDS instance class

  DBMasterPassword:
    Type: String
    NoEcho: true
    MinLength: 32
    Description: RDS master password

  AdminIPWhitelist:
    Type: String
    Default: 203.0.113.0/24
    Description: IP range allowed to SSH

  DomainName:
    Type: String
    Default: gbstudio.yourdomain.com
    Description: Domain name for the application

Resources:
  # VPC
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-vpc

  # Internet Gateway
  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-igw

  AttachGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  # Public Subnets
  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-public-subnet-1

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-public-subnet-2

  # Private Subnets
  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.10.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-private-subnet-1

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.11.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-private-subnet-2

  # Route Tables
  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-public-rt

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: AttachGateway
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PublicSubnetRouteTableAssociation1:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref PublicRouteTable

  PublicSubnetRouteTableAssociation2:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet2
      RouteTableId: !Ref PublicRouteTable

  # Security Groups
  ALBSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for ALB
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-alb-sg

  EC2SecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for EC2 instances
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 8000
          ToPort: 8000
          SourceSecurityGroupId: !Ref ALBSecurityGroup
        - IpProtocol: tcp
          FromPort: 22
          ToPort: 22
          CidrIp: !Ref AdminIPWhitelist
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-ec2-sg

  # RDS
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Subnet group for RDS
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-db-subnet

  RDSSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for RDS
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref EC2SecurityGroup
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-rds-sg

  DBInstance:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: !Sub ${Environment}-gbstudio-db
      Engine: postgres
      EngineVersion: '15.4'
      DBInstanceClass: !Ref DBInstanceClass
      AllocatedStorage: 100
      StorageType: gp3
      StorageEncrypted: true
      DBName: gbstudio_production
      MasterUsername: gbstudio_admin
      MasterUserPassword: !Ref DBMasterPassword
      DBSubnetGroupName: !Ref DBSubnetGroup
      VPCSecurityGroups:
        - !Ref RDSSecurityGroup
      BackupRetentionPeriod: 30
      PreferredBackupWindow: 03:00-04:00
      PreferredMaintenanceWindow: sun:04:00-sun:05:00
      DeletionProtection: true
      Tags:
        - Key: Name
          Value: !Sub ${Environment}-gbstudio-db

Outputs:
  VPCId:
    Description: VPC ID
    Value: !Ref VPC
    Export:
      Name: !Sub ${Environment}-VPC-ID

  DBEndpoint:
    Description: RDS endpoint
    Value: !GetAtt DBInstance.Endpoint.Address
    Export:
      Name: !Sub ${Environment}-DB-Endpoint
```

---

## 5. Docker Swarm

### 5.1 Stack File

```yaml
# docker-stack.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=gbstudio_prod
      - POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
      - POSTGRES_DB=gbstudio_production
    secrets:
      - postgres_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - backend
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.type == database
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass $(cat /run/secrets/redis_password)
    secrets:
      - redis_password
    volumes:
      - redis_data:/data
    networks:
      - backend
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '1.0'
          memory: 2G

  backend:
    image: ghcr.io/your-org/gbstudio/backend:v3.2.0
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql+asyncpg://gbstudio_prod:$(cat /run/secrets/postgres_password)@postgres:5432/gbstudio_production
    secrets:
      - postgres_password
      - redis_password
      - api_key_secret
    volumes:
      - project_files:/app/project_files
      - vectorstore:/app/vectorstore
      - logs:/app/logs
    networks:
      - backend
      - frontend
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
        reservations:
          cpus: '2.0'
          memory: 2G

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    networks:
      - frontend
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

networks:
  frontend:
    driver: overlay
  backend:
    driver: overlay
    internal: true

volumes:
  postgres_data:
  redis_data:
  project_files:
  vectorstore:
  logs:

secrets:
  postgres_password:
    external: true
  redis_password:
    external: true
  api_key_secret:
    external: true
```

### 5.2 Deployment Commands

```bash
# Initialize Swarm
docker swarm init

# Create secrets
echo "your_postgres_password" | docker secret create postgres_password -
echo "your_redis_password" | docker secret create redis_password -
echo "your_api_key" | docker secret create api_key_secret -

# Deploy stack
docker stack deploy -c docker-stack.yml gbstudio

# Scale service
docker service scale gbstudio_backend=5

# Update service
docker service update --image ghcr.io/your-org/gbstudio/backend:v3.2.1 gbstudio_backend

# View logs
docker service logs -f gbstudio_backend

# Remove stack
docker stack rm gbstudio
```

---

## 6. Ansible Playbooks

### 6.1 Inventory

```ini
# inventory/production.ini
[production]
gbstudio-prod-1 ansible_host=203.0.113.10 ansible_user=ubuntu

[production:vars]
environment=production
domain_name=gbstudio.yourdomain.com
```

### 6.2 Main Playbook

```yaml
# playbooks/deploy.yml
---
- name: Deploy GBStudio Production
  hosts: production
  become: yes
  vars_files:
    - ../vars/production.yml

  tasks:
    - name: Update system packages
      apt:
        update_cache: yes
        upgrade: dist

    - name: Install dependencies
      apt:
        name:
          - docker.io
          - docker-compose
          - nginx
          - certbot
          - python3-certbot-nginx
        state: present

    - name: Create application directory
      file:
        path: /data/gbstudio
        state: directory
        mode: '0755'

    - name: Copy docker-compose file
      template:
        src: ../templates/docker-compose.production.yml.j2
        dest: /data/gbstudio/docker-compose.yml
        mode: '0644'

    - name: Copy environment file
      template:
        src: ../templates/.env.production.j2
        dest: /data/gbstudio/.env
        mode: '0600'

    - name: Deploy containers
      community.docker.docker_compose:
        project_src: /data/gbstudio
        state: present
        pull: yes

    - name: Configure nginx
      template:
        src: ../templates/nginx.conf.j2
        dest: /etc/nginx/sites-available/gbstudio
        mode: '0644'
      notify: reload nginx

    - name: Enable nginx site
      file:
        src: /etc/nginx/sites-available/gbstudio
        dest: /etc/nginx/sites-enabled/gbstudio
        state: link
      notify: reload nginx

    - name: Obtain SSL certificate
      command: certbot --nginx -d {{ domain_name }} --non-interactive --agree-tos --email admin@example.com
      args:
        creates: /etc/letsencrypt/live/{{ domain_name }}/fullchain.pem

  handlers:
    - name: reload nginx
      service:
        name: nginx
        state: reloaded
```

---

**End of Infrastructure as Code Documentation**

For production deployment, see `PRODUCTION_DEPLOYMENT.md`.
