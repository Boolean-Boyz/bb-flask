# Deployment Commands for EC2 Server

## 1. Install Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker
```

## 2. Clone and Run Backend

```bash
cd ~
git clone https://github.com/Boolean-Boyz/bb-flask.git
cd bb-flask
docker compose up --build -d
```

Verify:
```bash
docker compose ps
curl http://localhost:8415
```

## 3. Install and Configure Nginx

```bash
sudo apt-get install -y nginx
sudo cp ~/bb-flask/nginx_for_flask_8587 /etc/nginx/sites-available/flask
sudo ln -s /etc/nginx/sites-available/flask /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## 4. Route 53 DNS (AWS Console)

1. Go to **Route 53** → **Hosted Zones** → select your domain
2. Click **Create record**:
   - **Record name**: `flask`
   - **Record type**: `A`
   - **Value**: your EC2 public IP
   - **TTL**: `300`
3. Click **Create records**

## 5. HTTPS with Certbot

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d flask.opencodingsociety.com
```

## 6. Verify

```bash
curl https://flask.opencodingsociety.com
```

## To Update Later (after pushing new code)

```bash
cd ~/bb-flask
git pull
docker compose up --build -d
```
