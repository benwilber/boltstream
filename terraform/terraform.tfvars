ssh_public_key      = "~/.ssh/id_rsa-boltstream.me.pub"
domain              = "boltstream.me"
region              = "nyc3"

droplet_images = {
    web     = "centos-7-x64"
    storage = "centos-7-x64"
}

droplet_sizes = {
    web     = "4gb"
    storage = "4gb"
}

web_droplet_count = 1

storage_size = 100

env          = "prod"

project_envs = {
    prod    = "production"
    staging = "staging"
    dev     = "development"
}

repo_url     = "git@github.com:benwilber/boltstream.git"

deploy_key   = "files/id_rsa-ansible-pull"

web_deploy_tags     = ["common", "web"]

storage_deploy_tags = ["common", "storage", "database", "cache"]

# Add your SSH IPs addresses here
allowed_ips  = []
