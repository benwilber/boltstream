# Boltstream
Self-hosted Live Video Streaming Website + Backend

Reference website: [https://boltstream.me](https://boltstream.me)

This is the result of a series of blog posts that I made [here](https://benwilber.github.io/nginx/rtmp/live/video/streaming/2018/03/25/building-a-live-video-streaming-website-part-1-start-streaming.html)

## Features

* Live stream via RTMP with a stream key to your RTMP ingest server
* Any number of simultaneous live streams
* Playback via standard HLS
* Restrict playback with HLS segment encryption (AES-128)
	* Pay-per-view
	* Pay-per-minute :-)
* Capture VODs (recordings) of live streams
	* Live-clipping of VODs via nginx-vod-module
* Timed metadata via WebVTT
	* Synchronized chat room messages
	* Synchronized play-by-play live sports events


## Core Components

* [Django](https://www.djangoproject.com/)
	* Web application
* [nginx](https://nginx.org/)
	* Web server
* [nginx-rtmp](https://github.com/arut/nginx-rtmp-module)
	* RTMP ingest
	* Actually, we use a [fork](https://github.com/sergey-dryabzhinsky/nginx-rtmp-module) that adds a number of features that we use.  The original nginx-rtmp hasn't been updated in years.
* [nginx-vod-module](https://github.com/kaltura/nginx-vod-module)
	* HLS VODs
	* Live clipping
* [FFMPEG](https://ffmpeg.org/)
	* Various video encoding/packaging

## Optional Components

* [SportRadar](https://www.sportradar.com/)
	* Realtime sports play-by-play data synchronized to your live streams
* [ACRCloud](https://www.acrcloud.com/)
	* Audio content recognition (Shazaam for your live streams)

	
## Getting Started

Clone this repo!

#### Terraform / Ansible
There is a [Terraform](https://terraform.io/) configuration for deploying this infrastructure on [DigitalOcean](https://www.digitalocean.com/).

First, edit `ansible/site.yml` and update all the variables like `<your ...variable_here>`.

You will also need to modify some variables in `terraform/terraform.tfvars`, and then from within the `terraform` directory, just run:

```bash
$ make apply
```

#### Docker

Will take a long time to build nginx/ffmpeg but only required once. 

Modify your `.env` to suit your needs.

```
git clone https://github.com/nitrag/boltstream.git
git checkout dockerize
docker-compose build
docker-compose up -d
docker-compose stop boltstream
docker-compose run boltstream python manage.py migrate 
docker-compose run boltstream python manage.py createsuperuser
docker-compose up -d
```

At the end of the Terraform deployment (might take 10-15 minutes), you will have a full self-hosted live video streaming platform with your own RTMP ingest and playback endpoints.

Happy Streaming!

## Help Wanted!

Help me package this up!  We need more federated live-streaming platforms!  It can't just always be Twitch.tv, YouTube, and Facebook!