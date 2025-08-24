# Linescope Server 生产环境部署指南

本文档描述了如何将 Linescope Server 部署到生产环境中，包括 Docker、Kubernetes 和传统服务器部署方式。

## 🚀 快速开始

### 使用 Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd Linescope_Server

# 2. 配置环境变量
cp production.env .env
# 编辑 .env 文件，设置必要的配置

# 3. 执行部署
chmod +x deploy.sh
./deploy.sh production deploy

# 4. 验证部署
./deploy.sh production status
```

访问 http://localhost 查看应用。

## 📋 部署方式对比

| 部署方式 | 适用场景 | 优点 | 缺点 |
|---------|----------|------|------|
| Docker Compose | 中小型部署 | 简单快速，易于管理 | 单机限制 |
| Kubernetes | 大规模生产 | 高可用，自动扩缩容 | 复杂度高 |
| 传统部署 | 简单环境 | 直接控制，调试方便 | 手动管理，扩展性差 |

## 🐳 Docker 部署

### 1. 系统要求

- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **内存**: 最低 2GB，推荐 4GB+
- **CPU**: 最低 2 核，推荐 4 核+
- **存储**: 最低 10GB，推荐 50GB+

### 2. 安装 Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# CentOS/RHEL
sudo yum install -y docker docker-compose
sudo systemctl enable --now docker
```

### 3. 部署配置

#### 环境变量配置

复制并编辑环境变量文件：

```bash
cp production.env .env
```

关键配置项：

```bash
# 安全配置
SECRET_KEY=your-super-secret-key-change-this-in-production

# 性能配置
WORKERS=4
WORKER_CLASS=gthread
THREADS=2

# 数据配置
DATA_STORE_INTERVAL_MINUTES=30
STREAM_FRAME_INTERVAL_SEC=0.2
```

#### Docker Compose 配置

主要服务配置：

- **linescope-server**: 主应用服务（4 个工作进程）
- **nginx**: 反向代理和静态文件服务
- **redis**: 缓存和会话存储

### 4. 部署命令

```bash
# 完整部署
./deploy.sh production deploy

# 仅查看状态
./deploy.sh production status

# 回滚部署
./deploy.sh production rollback

# 清理资源
./deploy.sh production cleanup
```

### 5. 监控和日志

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f linescope-server

# 查看资源使用
docker stats

# 执行健康检查
./monitoring/health-check.sh
```

## ☸️ Kubernetes 部署

### 1. 先决条件

- Kubernetes 集群 (v1.25+)
- kubectl 配置正确
- Helm (可选，用于包管理)
- 持久卷存储类 (fast-ssd)

### 2. 部署步骤

```bash
# 1. 创建命名空间和资源
kubectl apply -f k8s-deployment.yaml

# 2. 验证部署
kubectl get pods -n linescope
kubectl get services -n linescope
kubectl get ingress -n linescope

# 3. 查看日志
kubectl logs -f deployment/linescope-server -n linescope

# 4. 扩缩容
kubectl scale deployment/linescope-server --replicas=5 -n linescope
```

### 3. 配置说明

#### 资源配置

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi" 
    cpu: "500m"
```

#### 自动扩缩容

- **最小副本数**: 2
- **最大副本数**: 10
- **CPU 阈值**: 70%
- **内存阈值**: 80%

#### 持久化存储

- **应用数据**: 5Gi (fast-ssd)
- **Redis 数据**: 1Gi (fast-ssd)

### 4. 网络配置

使用 Nginx Ingress Controller：

```bash
# 安装 Ingress Controller
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace

# 配置域名
# 编辑 k8s-deployment.yaml 中的 your-domain.com
```

## 🖥️ 传统服务器部署

### 1. 系统准备

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y python3.11 python3.11-venv nginx redis-server

# CentOS/RHEL
sudo yum install -y python3.11 python3.11-venv nginx redis
```

### 2. 应用部署

```bash
# 1. 创建应用用户
sudo useradd -m -s /bin/bash linescope
sudo su - linescope

# 2. 部署应用
git clone <repository-url> /opt/linescope
cd /opt/linescope

# 3. 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements-production.txt

# 4. 配置环境
cp production.env .env
# 编辑配置文件

# 5. 测试运行
python -m flask --app core/factory.py run
```

### 3. 系统服务配置

#### Systemd 服务文件

```bash
sudo tee /etc/systemd/system/linescope.service << 'EOF'
[Unit]
Description=Linescope Server
After=network.target

[Service]
Type=exec
User=linescope
Group=linescope
WorkingDirectory=/opt/linescope
Environment=PATH=/opt/linescope/venv/bin
ExecStart=/opt/linescope/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --worker-class gthread --threads 2 'core.factory:create_app()'
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl enable --now linescope
sudo systemctl status linescope
```

#### Nginx 配置

```bash
# 复制 Nginx 配置
sudo cp nginx.conf /etc/nginx/sites-available/linescope
sudo ln -s /etc/nginx/sites-available/linescope /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

## 🔒 安全配置

### 1. SSL/TLS 配置

#### Let's Encrypt 证书

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 自签名证书（测试环境）

```bash
# 创建证书目录
sudo mkdir -p /etc/nginx/ssl

# 生成自签名证书
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/key.pem \
  -out /etc/nginx/ssl/cert.pem
```

### 2. 防火墙配置

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

### 3. 安全头配置

在 Nginx 配置中已包含：

- X-Frame-Options
- X-XSS-Protection
- X-Content-Type-Options
- Referrer-Policy
- Content-Security-Policy
- Strict-Transport-Security (HTTPS)

## 📊 性能优化

### 1. 应用层优化

- **工作进程数**: CPU 核心数 × 2
- **线程数**: 每进程 2-4 个线程
- **连接复用**: Keep-alive 启用
- **缓存策略**: Redis 缓存 + Nginx 静态缓存

### 2. 数据库优化

如果使用数据库：

```bash
# PostgreSQL 优化
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

### 3. 系统层优化

```bash
# 内核参数优化
echo 'net.core.somaxconn = 65535' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_max_syn_backlog = 65535' >> /etc/sysctl.conf
echo 'fs.file-max = 65535' >> /etc/sysctl.conf
sysctl -p

# 用户限制
echo 'linescope soft nofile 65535' >> /etc/security/limits.conf
echo 'linescope hard nofile 65535' >> /etc/security/limits.conf
```

## 🔍 监控和故障排除

### 1. 健康检查

```bash
# 自动健康检查脚本
./monitoring/health-check.sh

# 手动检查
curl -f http://localhost/healthz
```

### 2. 日志管理

```bash
# 应用日志
tail -f /opt/linescope/app.log

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# 系统日志
journalctl -u linescope -f
```

### 3. 性能监控

```bash
# 资源使用情况
htop
iotop
netstat -tulpn

# 应用性能
curl -w "@curl-format.txt" -o /dev/null -s http://localhost/

# curl-format.txt 内容:
#      time_namelookup:  %{time_namelookup}\n
#         time_connect:  %{time_connect}\n
#      time_appconnect:  %{time_appconnect}\n
#     time_pretransfer:  %{time_pretransfer}\n
#        time_redirect:  %{time_redirect}\n
#   time_starttransfer:  %{time_starttransfer}\n
#                     ------\n
#           time_total:  %{time_total}\n
```

### 4. 常见问题

#### 应用启动失败

```bash
# 检查日志
journalctl -u linescope --no-pager
docker-compose logs linescope-server

# 检查端口占用
sudo netstat -tulpn | grep :5000

# 检查文件权限
ls -la /opt/linescope/
```

#### 性能问题

```bash
# 查看资源使用
docker stats
top -p $(pgrep -f gunicorn)

# 查看连接数
ss -tuln
netstat -an | grep :80 | wc -l
```

#### 网络问题

```bash
# 检查服务状态
systemctl status nginx linescope redis

# 检查网络连通性
curl -I http://localhost
telnet localhost 5000
```

## 🚀 扩容策略

### 1. 垂直扩容

增加服务器资源：

```bash
# 增加工作进程
export WORKERS=8
docker-compose up -d --scale linescope-server=1

# Kubernetes
kubectl patch deployment linescope-server -n linescope -p '{"spec":{"template":{"spec":{"containers":[{"name":"linescope-server","resources":{"requests":{"memory":"512Mi","cpu":"500m"},"limits":{"memory":"1Gi","cpu":"1000m"}}}]}}}}'
```

### 2. 水平扩容

增加服务器节点：

```bash
# Docker Compose (多服务器)
# 使用 Docker Swarm 模式
docker swarm init
docker stack deploy -c docker-compose.yml linescope

# Kubernetes
kubectl scale deployment linescope-server --replicas=6 -n linescope
```

### 3. 负载均衡

```bash
# Nginx 负载均衡配置
upstream linescope_backend {
    least_conn;
    server 192.168.1.10:5000 max_fails=3 fail_timeout=30s;
    server 192.168.1.11:5000 max_fails=3 fail_timeout=30s;
    server 192.168.1.12:5000 max_fails=3 fail_timeout=30s;
}
```

## 📝 备份和恢复

### 1. 数据备份

```bash
# 自动备份脚本
#!/bin/bash
BACKUP_DIR="/opt/backups/linescope"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/data_$DATE.tar.gz /opt/linescope/utils/data/
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /opt/linescope/.env /etc/nginx/sites-available/linescope

# 清理旧备份（保留 30 天）
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### 2. 数据恢复

```bash
# 停止服务
sudo systemctl stop linescope nginx

# 恢复数据
tar -xzf /opt/backups/linescope/data_20240101_120000.tar.gz -C /

# 恢复配置
tar -xzf /opt/backups/linescope/config_20240101_120000.tar.gz -C /

# 启动服务
sudo systemctl start linescope nginx
```

## 🔄 更新和维护

### 1. 应用更新

```bash
# Docker 方式
git pull
./deploy.sh production deploy

# 传统方式
sudo systemctl stop linescope
cd /opt/linescope
git pull
source venv/bin/activate
pip install -r requirements-production.txt
sudo systemctl start linescope
```

### 2. 系统维护

```bash
# 定期维护任务（crontab）
0 2 * * * /opt/linescope/scripts/cleanup.sh
0 3 * * 0 /opt/linescope/scripts/backup.sh
*/15 * * * * /opt/linescope/monitoring/health-check.sh
```

## 📞 支持和联系

- **GitHub Issues**: <repository-url>/issues
- **文档**: 查看项目 README.md 和 CLAUDE.md
- **日志**: 检查应用和系统日志获取详细信息

---

**注意**: 在生产环境中，请确保：
1. 修改所有默认密码和密钥
2. 定期更新系统和依赖包
3. 配置适当的监控和告警
4. 实施定期备份策略
5. 遵循安全最佳实践