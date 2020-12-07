variable "ssh_public_key" {}
variable "domain" {}
variable "region" {}
variable "droplet_images" { type = map }
variable "droplet_sizes" { type = map }
variable "web_droplet_count" {}
variable "storage_size" {}
variable "env" {}
variable "project_envs" { type = map }
variable "deploy_key" {}
variable "web_deploy_tags" { type = list }
variable "storage_deploy_tags" { type = list }
variable "repo_url" {}
variable "allowed_ips" { type = list }

resource "digitalocean_ssh_key" "ssh_key" {
  name       = var.domain
  public_key = file(var.ssh_public_key)
}

data "local_file" "deploy_key" {
  filename = var.deploy_key
}

data "template_file" "web_user_data" {
  template = file("files/user-data.sh.txt")
  vars     = {
    region      = var.region
    domain      = var.domain
    env         = var.env
    deploy_key  = data.local_file.deploy_key.content
    repo_url    = var.repo_url
    tags        = join(",", var.web_deploy_tags)
  }
}

data "template_file" "storage_user_data" {
  template = file("files/user-data.sh.txt")
  vars = {
    region      = var.region
    domain      = var.domain
    env         = var.env
    deploy_key  = data.local_file.deploy_key.content
    repo_url    = var.repo_url
    tags        = join(",", var.storage_deploy_tags)
  }
}

resource "digitalocean_project" "project" {
  name        = "${var.region}-${var.env}-${replace(var.domain, ".", "-")}"
  description = "${var.region}-${var.env}-${replace(var.domain, ".", "-")}"
  purpose     = "Web Application"
  environment = var.project_envs[var.env]
  resources   = concat([
    digitalocean_domain.domain.urn,
    digitalocean_spaces_bucket.bucket.urn,
    digitalocean_droplet.storage_droplet.urn,
    digitalocean_volume.storage_volume.urn,
    digitalocean_loadbalancer.loadbalancer.urn
  ], digitalocean_droplet.web_droplet.*.urn)
}

resource "digitalocean_tag" "site_tag" {
  name = replace(var.domain, ".", "-")
}

resource "digitalocean_tag" "region_tag" {
  name = "${var.region}-${replace(var.domain, ".", "-")}"
}

resource "digitalocean_tag" "env_tag" {
  name = "${var.env}-${replace(var.domain, ".", "-")}"
}

resource "digitalocean_tag" "region_env_tag" {
  name = "${var.region}-${var.env}-${replace(var.domain, ".", "-")}"
}

resource "digitalocean_spaces_bucket" "bucket" {
  region        = var.region
  name          = "${var.region}-${var.env}-${replace(var.domain, ".", "-")}"
  acl           = "private"
  force_destroy = true
}

resource "digitalocean_cdn" "cdn" {
  origin         = digitalocean_spaces_bucket.bucket.bucket_domain_name
  custom_domain  = "cdn-${var.region}-${var.env}.${var.domain}"
  certificate_name = digitalocean_certificate.certificate.name
}

resource "digitalocean_volume" "storage_volume" {
  region                   = var.region
  name                     = "storage-${var.region}-${var.env}-${replace(var.domain, ".", "-")}"
  size                     = var.storage_size
  initial_filesystem_type  = "ext4"
  initial_filesystem_label = "s-${var.region}-${var.env}"
}

resource "digitalocean_volume_attachment" "storage_volume_attachment" {
  droplet_id = digitalocean_droplet.storage_droplet.id
  volume_id  = digitalocean_volume.storage_volume.id
}

resource "digitalocean_droplet" "storage_droplet" {
  image              = var.droplet_images["storage"]
  name               = "storage-${var.region}-${var.env}.${var.domain}"
  region             = var.region
  size               = var.droplet_sizes["storage"]
  ipv6               = true
  private_networking = true
  monitoring         = true
  ssh_keys           = [digitalocean_ssh_key.ssh_key.fingerprint]
  user_data          = data.template_file.storage_user_data.rendered
  tags               = [
    digitalocean_tag.site_tag.name,
    digitalocean_tag.region_tag.name,
    digitalocean_tag.env_tag.name,
    digitalocean_tag.region_env_tag.name,
    "storage-${digitalocean_tag.site_tag.name}",    
    "storage-${digitalocean_tag.region_tag.name}",
    "storage-${digitalocean_tag.env_tag.name}",
    "storage-${digitalocean_tag.region_env_tag.name}",
    "database-${digitalocean_tag.site_tag.name}",    
    "database-${digitalocean_tag.region_tag.name}",
    "database-${digitalocean_tag.env_tag.name}",
    "database-${digitalocean_tag.region_env_tag.name}",
    "cache-${digitalocean_tag.site_tag.name}",    
    "cache-${digitalocean_tag.region_tag.name}",
    "cache-${digitalocean_tag.env_tag.name}",
    "cache-${digitalocean_tag.region_env_tag.name}"
  ]
}

resource "digitalocean_droplet" "web_droplet" {
  image              = var.droplet_images["web"]
  name               = "web-${format("%02d", count.index)}-${var.region}-${var.env}.${var.domain}"
  region             = var.region
  size               = var.droplet_sizes["web"]
  ipv6               = true
  private_networking = true
  monitoring         = true
  ssh_keys           = [digitalocean_ssh_key.ssh_key.fingerprint]
  user_data          = data.template_file.web_user_data.rendered
  tags               = [
    digitalocean_tag.site_tag.name,
    digitalocean_tag.region_tag.name,
    digitalocean_tag.env_tag.name,
    digitalocean_tag.region_env_tag.name,
    "web-${digitalocean_tag.site_tag.name}",    
    "web-${digitalocean_tag.region_tag.name}",
    "web-${digitalocean_tag.env_tag.name}",
    "web-${digitalocean_tag.region_env_tag.name}"
  ]
  depends_on = [digitalocean_droplet.storage_droplet]
  count      = var.web_droplet_count
}

resource "digitalocean_firewall" "firewall" {
  name = "${var.region}-${var.env}.${var.domain}"
  tags = [
    digitalocean_tag.site_tag.name,
    digitalocean_tag.region_tag.name,
    digitalocean_tag.env_tag.name,
    digitalocean_tag.region_env_tag.name
  ]

  inbound_rule {
      protocol         = "tcp"
      port_range       = "80"
      source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
      protocol         = "tcp"
      port_range       = "443"
      source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
      protocol         = "tcp"
      port_range       = "1935"
      source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
      protocol         = "tcp"
      port_range       = "1-65535"
      source_addresses = var.allowed_ips
      source_tags      = [digitalocean_tag.region_env_tag.name]
  }

  inbound_rule {
      protocol         = "udp"
      port_range       = "1-65535"
      source_addresses = var.allowed_ips
      source_tags      = [digitalocean_tag.region_env_tag.name]
  }

  inbound_rule {
      protocol         = "icmp"
      port_range       = "1-65535"
      source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
      protocol              = "tcp"
      port_range            = "1-65535"
      destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
      protocol              = "udp"
      port_range            = "1-65535"
      destination_addresses = ["0.0.0.0/0", "::/0"]
    }

  outbound_rule {
      protocol              = "icmp"
      port_range            = "1-65535"
      destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

resource "digitalocean_certificate" "certificate" {
  name    = "${var.region}-${var.env}-${replace(var.domain, ".", "-")}"
  type    = "lets_encrypt"
  domains = [
    var.domain,
    "cdn.${var.domain}",
    "cdn-${var.region}-${var.env}.${var.domain}",
    "web-${var.region}-${var.env}.${var.domain}"
  ]

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [digitalocean_domain.domain]
}

resource "digitalocean_loadbalancer" "loadbalancer" {
  name                   = "${var.region}-${var.env}-${replace(var.domain, ".", "-")}"
  region                 = var.region
  algorithm              = "least_connections"
  redirect_http_to_https = true
  droplet_tag            = "web-${digitalocean_tag.region_env_tag.name}"

  forwarding_rule {
    entry_port      = 80
    entry_protocol  = "http"
    target_port     = 80
    target_protocol = "http"
  }

  forwarding_rule {
    entry_port      = 443
    entry_protocol  = "https"
    target_port     = 80
    target_protocol = "http"
    certificate_id  = digitalocean_certificate.certificate.id
  }

  forwarding_rule {
    entry_port      = 1935
    entry_protocol  = "tcp"
    target_port     = 1935
    target_protocol = "tcp"
  }

  healthcheck {
    port     = 80
    protocol = "http"
    path     = "/app-health"
  }
}

resource "digitalocean_domain" "domain" {
  name = var.domain
}

resource "digitalocean_record" "web_ipv4_record" {
  domain = digitalocean_domain.domain.id
  type   = "A"
  ttl    = "300"
  name   = "web-${var.region}-${var.env}"
  value  = digitalocean_loadbalancer.loadbalancer.ip
}

resource "digitalocean_record" "web_droplet_ipv4_record" {
  domain = digitalocean_domain.domain.id
  type   = "A"
  ttl    = "300"
  name   = "web-${format("%02d", count.index)}-${var.region}-${var.env}"
  value  = element(digitalocean_droplet.web_droplet.*.ipv4_address, count.index)
  count  = var.web_droplet_count
}

resource "digitalocean_record" "web_droplet_private_ipv4_record" {
  domain = digitalocean_domain.domain.id
  type   = "A"
  ttl    = "300"
  name   = "web-${format("%02d", count.index)}-internal-${var.region}-${var.env}"
  value  = element(digitalocean_droplet.web_droplet.*.ipv4_address_private, count.index)
  count  = var.web_droplet_count
}

resource "digitalocean_record" "web_droplet_ipv6_record" {
  domain = digitalocean_domain.domain.id
  type   = "AAAA"
  ttl    = "300"
  name   = "web-${format("%02d", count.index)}-${var.region}-${var.env}"
  value  = element(digitalocean_droplet.web_droplet.*.ipv6_address, count.index)
  count  = var.web_droplet_count
}

resource "digitalocean_record" "storage_droplet_ipv4_record" {
  domain = digitalocean_domain.domain.id
  type   = "A"
  ttl    = "300"
  name   = "storage-${var.region}-${var.env}"
  value  = digitalocean_droplet.storage_droplet.ipv4_address
}

resource "digitalocean_record" "storage_droplet_ipv6_record" {
  domain = digitalocean_domain.domain.id
  type   = "AAAA"
  ttl    = "300"
  name   = "storage-${var.region}-${var.env}"
  value  = digitalocean_droplet.storage_droplet.ipv6_address
}

resource "digitalocean_record" "storage_droplet_private_ipv4_record" {
  domain = digitalocean_domain.domain.id
  type   = "A"
  ttl    = "300"
  name   = "storage-internal-${var.region}-${var.env}"
  value  = digitalocean_droplet.storage_droplet.ipv4_address_private
}

resource "digitalocean_record" "database_droplet_ipv4_record" {
  domain = digitalocean_domain.domain.id
  type   = "A"
  ttl    = "300"
  name   = "database-${var.region}-${var.env}"
  value  = digitalocean_droplet.storage_droplet.ipv4_address
}

resource "digitalocean_record" "database_droplet_ipv6_record" {
  domain = digitalocean_domain.domain.id
  type   = "AAAA"
  ttl    = "300"
  name   = "database-${var.region}-${var.env}"
  value  = digitalocean_droplet.storage_droplet.ipv6_address
}

resource "digitalocean_record" "database_droplet_private_ipv4_record" {
  domain = digitalocean_domain.domain.id
  type   = "A"
  ttl    = "300"
  name   = "database-internal-${var.region}-${var.env}"
  value  = digitalocean_droplet.storage_droplet.ipv4_address_private
}

resource "digitalocean_record" "cache_droplet_ipv4_record" {
  domain = digitalocean_domain.domain.id
  type   = "A"
  ttl    = "300"
  name   = "cache-${var.region}-${var.env}"
  value  = digitalocean_droplet.storage_droplet.ipv4_address
}

resource "digitalocean_record" "cache_droplet_ipv6_record" {
  domain = digitalocean_domain.domain.id
  type   = "AAAA"
  ttl    = "300"
  name   = "cache-${var.region}-${var.env}"
  value  = digitalocean_droplet.storage_droplet.ipv6_address
}

resource "digitalocean_record" "cache_droplet_private_ipv4_record" {
  domain = digitalocean_domain.domain.id
  type   = "A"
  ttl    = "300"
  name   = "cache-internal-${var.region}-${var.env}"
  value  = digitalocean_droplet.storage_droplet.ipv4_address_private
}
